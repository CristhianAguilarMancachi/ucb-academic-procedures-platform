import hashlib
import logging
import re
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from app.services.rag.embeddings import generate_embeddings


def calculate_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def extract_text_by_page(
    file_path: str | Path,
) -> list[dict]:
    path = Path(file_path)
    pdf = fitz.open(path)
    pages = []

    try:
        for page_index in range(len(pdf)):
            page = pdf.load_page(page_index)
            text = page.get_text("text")

            pages.append(
                {
                    "page_number": page_index + 1,
                    "text": text.strip(),
                }
            )
    finally:
        pdf.close()

    return pages


def has_meaningful_text(
    pages: list[dict],
    min_total_chars: int = 400,
) -> bool:
    total_chars = sum(
        len(page["text"].strip())
        for page in pages
    )

    non_empty_pages = sum(
        1
        for page in pages
        if page["text"].strip()
    )

    if total_chars < min_total_chars:
        return False

    return non_empty_pages > 0


logger = logging.getLogger(__name__)

OCR_DPI = 170
OCR_FALLBACK_DPI = 130
OCR_TIMEOUT_SECONDS = 35
OCR_FALLBACK_TIMEOUT_SECONDS = 25
OCR_MIN_ALNUM = 12
OCR_IMAGE_COVERAGE = 0.20


@lru_cache(maxsize=1)
def get_ocr_languages() -> str:
    """Valida Tesseract y el idioma español una vez."""
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR no está disponible."
        ) from exc

    if "spa" not in languages:
        raise RuntimeError(
            "Falta el idioma español de Tesseract. "
            "Reconstruye el backend con tesseract-ocr-spa."
        )

    return "spa+eng" if "eng" in languages else "spa"


def useful_characters(text: str) -> int:
    return sum(character.isalnum() for character in text)


def image_coverage(page) -> float:
    """Estimación de la superficie ocupada por imágenes."""
    total_area = page.rect.get_area()

    if total_area <= 0:
        return 0.0

    image_area = 0.0

    for image in page.get_image_info():
        rectangle = fitz.Rect(image["bbox"]) & page.rect

        if not rectangle.is_empty:
            image_area += rectangle.get_area()

    return min(1.0, image_area / total_area)


def page_requires_ocr(
    native_text: str,
    coverage: float,
) -> bool:
    """No ejecutar OCR por tener simplemente una imagen decorativa."""
    count = useful_characters(native_text)

    if coverage >= OCR_IMAGE_COVERAGE and count < 350:
        return True

    if count < OCR_MIN_ALNUM and coverage > 0:
        return True

    return False


def recognize_page(page, languages: str) -> str:
    """Reconoce páginas con un segundo intento acotado ante timeout."""
    longest = max(page.rect.width, page.rect.height, 1)
    max_dpi = max(90, int(4600 * 72 / longest))
    attempts = (
        (min(OCR_DPI, max_dpi), OCR_TIMEOUT_SECONDS),
        (min(OCR_FALLBACK_DPI, max_dpi), OCR_FALLBACK_TIMEOUT_SECONDS),
    )

    for attempt, (dpi, timeout_seconds) in enumerate(attempts, start=1):
        started_at = time.monotonic()
        pixmap = page.get_pixmap(
            dpi=dpi,
            colorspace=fitz.csRGB,
            alpha=False,
        )

        try:
            with Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            ) as image:
                result = pytesseract.image_to_string(
                    image,
                    lang=languages,
                    config="--psm 3",
                    timeout=timeout_seconds,
                )
        except RuntimeError as exc:
            if "Tesseract process timeout" not in str(exc):
                raise
            logger.warning(
                "[RAG][OCR] timeout intento=%s dpi=%s "
                "limite_s=%s duracion_s=%.1f",
                attempt,
                dpi,
                timeout_seconds,
                time.monotonic() - started_at,
            )
            if attempt == len(attempts):
                raise
            continue
        finally:
            del pixmap

        logger.info(
            "[RAG][OCR] completado intento=%s dpi=%s "
            "duracion_s=%.1f caracteres=%s",
            attempt,
            dpi,
            time.monotonic() - started_at,
            useful_characters(result),
        )
        return result.strip()

    raise RuntimeError("No se completó el OCR de la página.")


def extract_text_by_page_with_ocr(
    file_path: str | Path,
    page_numbers: list[int] | None = None,
) -> list[dict]:
    """Mantiene compatibilidad con la extracción OCR explícita."""
    pages = []

    with fitz.open(file_path) as pdf:
        numbers = (
            list(range(1, len(pdf) + 1))
            if page_numbers is None
            else page_numbers
        )

        if any(number < 1 or number > len(pdf) for number in numbers):
            raise ValueError("Número de página fuera del PDF.")

        languages = get_ocr_languages() if numbers else ""

        for number in numbers:
            text = recognize_page(
                pdf[number - 1],
                languages,
            )

            pages.append({
                "page_number": number,
                "text": text,
            })

    return pages


def extract_text_by_page_hybrid(
    file_path: str | Path,
) -> list[dict]:
    """
    Extracción híbrida independiente del documento.

    - Primero intenta texto digital.
    - Evalúa imágenes por página.
    - Ejecuta OCR solo cuando corresponde.
    - Conserva el número de página original.
    - No modifica ni duplica el PDF.
    - Detiene una ingesta si falla el OCR necesario.
    """
    pages = []
    digital_count = 0
    ocr_count = 0
    empty_count = 0
    languages = None

    with fitz.open(file_path) as pdf:
        for number, page in enumerate(pdf, start=1):
            native_text = page.get_text("text").strip()
            coverage = image_coverage(page)

            selected_text = native_text
            used_ocr = False

            if page_requires_ocr(native_text, coverage):
                if languages is None:
                    languages = get_ocr_languages()

                try:
                    recognized_text = recognize_page(
                        page,
                        languages,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Falló el OCR de la página {number}. "
                        "Se canceló la ingesta para evitar "
                        "publicar información incompleta."
                    ) from exc

                native_count = useful_characters(native_text)
                recognized_count = useful_characters(recognized_text)

                # Se prefiere el OCR únicamente cuando recupera
                # contenido adicional significativo.
                if (
                    recognized_count >= OCR_MIN_ALNUM
                    and (
                        native_count < OCR_MIN_ALNUM
                        or recognized_count >= max(
                            native_count + 40,
                            int(native_count * 1.2),
                        )
                    )
                ):
                    selected_text = recognized_text
                    used_ocr = True

                # Un escaneo extenso con OCR ilegible no debe
                # considerarse una ingesta satisfactoria.
                if (
                    coverage >= 0.55
                    and useful_characters(selected_text)
                    < OCR_MIN_ALNUM
                ):
                    raise ValueError(
                        f"La página {number} contiene una "
                        "imagen extensa cuyo texto no pudo "
                        "recuperarse de manera suficiente."
                    )

            if used_ocr:
                ocr_count += 1
            elif selected_text.strip():
                digital_count += 1
            else:
                empty_count += 1

            pages.append({
                "page_number": number,
                "text": selected_text,
            })

    if not any(page["text"].strip() for page in pages):
        raise ValueError(
            "El PDF no contiene texto recuperable."
        )

    logger.info(
        "[RAG][PDF] paginas=%s digitales=%s "
        "ocr=%s sin_texto=%s",
        len(pages),
        digital_count,
        ocr_count,
        empty_count,
    )

    return pages


def clean_page_lines(
    lines: list[str],
) -> list[str]:
    """
    Limpieza conservadora para cualquier documento.

    No elimina títulos, encabezados institucionales,
    artículos, porcentajes, importes ni referencias.

    Solamente elimina líneas vacías y espacios
    horizontales redundantes.
    """
    cleaned = []

    for line in lines:
        normalized = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        if normalized:
            cleaned.append(normalized)

    return cleaned


def normalize_ocr_text(text: str) -> str:
    """
    Normalización no destructiva.

    Reglas:
    - Conservar símbolos y valores numéricos.
    - Conservar nombres y denominaciones oficiales.
    - Conservar artículos y referencias normativas.
    - No realizar sustituciones léxicas automáticas.
    - Mantener los saltos de línea.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)

    text = text.replace(
        "\\r\\n",
        "\\n",
    ).replace(
        "\\r",
        "\\n",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\\n{3,}",
        "\\n\\n",
        text,
    )

    return text.strip()


def normalize_page_text_content(
    pages: list[dict],
) -> list[dict]:
    normalized_pages = []

    for page in pages:
        normalized_pages.append(
            {
                "page_number": page["page_number"],
                "text": normalize_ocr_text(
                    page["text"]
                ),
            }
        )

    return normalized_pages


def normalize_pages_text(
    pages: list[dict],
) -> list[dict]:
    normalized_pages = []

    for page in pages:
        raw_lines = page["text"].splitlines()
        cleaned_lines = clean_page_lines(raw_lines)

        normalized_pages.append(
            {
                "page_number": page["page_number"],
                "text": "\n".join(
                    cleaned_lines
                ).strip(),
            }
        )

    return normalized_pages


def split_normative_blocks(
    pages: list[dict],
) -> list[dict]:
    blocks = []
    current_block = None
    current_section = None
    current_subsection = None
    chunk_number = 1

    article_pattern = re.compile(
        r"^(ART[IÍ]CULO\s+\d+[°º]?)",
        re.IGNORECASE,
    )

    chapter_pattern = re.compile(
        r"^(CAP[IÍ]TULO\s+[IVXLC\d]+)",
        re.IGNORECASE,
    )

    title_pattern = re.compile(
        r"^(T[IÍ]TULO\s+[IVXLC\d]+)",
        re.IGNORECASE,
    )

    for page in pages:
        page_number = page["page_number"]

        lines = [
            line.strip()
            for line in page["text"].splitlines()
            if line.strip()
        ]

        for line in lines:
            if title_pattern.match(line):
                current_section = line
                continue

            if chapter_pattern.match(line):
                current_subsection = line
                continue

            article_match = article_pattern.match(line)

            if article_match:
                if (
                    current_block
                    and current_block["content"].strip()
                ):
                    blocks.append(current_block)
                    chunk_number += 1

                current_block = {
                    "numero_chunk": chunk_number,
                    "pagina_inicio": page_number,
                    "pagina_fin": page_number,
                    "seccion": current_section,
                    "subseccion": current_subsection,
                    "articulo_numero": article_match.group(1),
                    "estrategia_chunking": (
                        "estructura_normativa"
                    ),
                    "content": line,
                }

                continue

            if current_block:
                current_block["content"] += (
                    "\n" + line
                )

                current_block["pagina_fin"] = page_number

    if (
        current_block
        and current_block["content"].strip()
    ):
        blocks.append(current_block)

    return refine_normative_blocks(
        blocks,
        max_words=180,
    )


def split_large_normative_block(
    block: dict,
    max_words: int = 180,
) -> list[dict]:
    content = block["content"].strip()

    paragraphs = [
        paragraph.strip()
        for paragraph in content.split("\n")
        if paragraph.strip()
    ]

    if len(content.split()) <= max_words:
        return [block]

    sub_blocks = []
    current_parts = []
    current_words = 0
    sub_index = 1

    for paragraph in paragraphs:
        paragraph_words = len(
            paragraph.split()
        )

        if (
            current_parts
            and current_words + paragraph_words
            > max_words
        ):
            new_block = block.copy()

            new_block["content"] = "\n".join(
                current_parts
            ).strip()

            if block.get("subseccion"):
                new_block["subseccion"] = (
                    f"{block['subseccion']} "
                    f"- parte {sub_index}"
                )
            else:
                new_block["subseccion"] = (
                    f"parte {sub_index}"
                )

            sub_blocks.append(new_block)
            sub_index += 1
            current_parts = [paragraph]
            current_words = paragraph_words
        else:
            current_parts.append(paragraph)
            current_words += paragraph_words

    if current_parts:
        new_block = block.copy()

        new_block["content"] = "\n".join(
            current_parts
        ).strip()

        if block.get("subseccion"):
            new_block["subseccion"] = (
                f"{block['subseccion']} "
                f"- parte {sub_index}"
            )
        else:
            new_block["subseccion"] = (
                f"parte {sub_index}"
            )

        sub_blocks.append(new_block)

    return sub_blocks


def refine_normative_blocks(
    blocks: list[dict],
    max_words: int = 180,
) -> list[dict]:
    refined = []

    for block in blocks:
        refined.extend(
            split_large_normative_block(
                block,
                max_words=max_words,
            )
        )

    for index, block in enumerate(
        refined,
        start=1,
    ):
        block["numero_chunk"] = index

    return refined


def split_lineamiento_blocks(
    pages: list[dict],
) -> list[dict]:
    blocks = []
    current_block = None
    chunk_number = 1
    current_section = None

    section_pattern = re.compile(
        r"^[A-Z]\.\s+"
    )

    numeral_pattern = re.compile(
        r"^\d+\.\s+"
    )

    for page in pages:
        page_number = page["page_number"]

        lines = [
            line.strip()
            for line in page["text"].splitlines()
            if line.strip()
        ]

        for line in lines:
            if section_pattern.match(line):
                current_section = line

                if (
                    current_block
                    and current_block["content"].strip()
                ):
                    blocks.append(current_block)
                    chunk_number += 1

                current_block = {
                    "numero_chunk": chunk_number,
                    "pagina_inicio": page_number,
                    "pagina_fin": page_number,
                    "seccion": current_section,
                    "subseccion": None,
                    "articulo_numero": None,
                    "estrategia_chunking": "lineamiento",
                    "content": line,
                }

                continue

            if numeral_pattern.match(line):
                if (
                    current_block
                    and current_block["content"].strip()
                ):
                    blocks.append(current_block)
                    chunk_number += 1

                current_block = {
                    "numero_chunk": chunk_number,
                    "pagina_inicio": page_number,
                    "pagina_fin": page_number,
                    "seccion": current_section,
                    "subseccion": line[:120],
                    "articulo_numero": None,
                    "estrategia_chunking": "lineamiento",
                    "content": line,
                }

                continue

            if current_block:
                current_block["content"] += (
                    "\n" + line
                )

                current_block["pagina_fin"] = page_number

    if (
        current_block
        and current_block["content"].strip()
    ):
        blocks.append(current_block)

    return blocks


def split_faq_blocks(
    pages: list[dict],
) -> list[dict]:
    blocks = []
    chunk_number = 1

    for page in pages:
        page_number = page["page_number"]
        raw_text = page["text"].strip()

        if not raw_text:
            continue

        sections = re.split(
            r"\n(?=-\s|\w.*:)",
            raw_text,
        )

        for section in sections:
            content = section.strip()

            if not content:
                continue

            first_line = (
                content.splitlines()[0][:120]
            )

            blocks.append(
                {
                    "numero_chunk": chunk_number,
                    "pagina_inicio": page_number,
                    "pagina_fin": page_number,
                    "seccion": "consultas_frecuentes",
                    "subseccion": first_line,
                    "articulo_numero": None,
                    "estrategia_chunking": (
                        "faq_tematico"
                    ),
                    "content": content,
                }
            )

            chunk_number += 1

    return blocks


def estimate_tokens(text: str) -> int:
    return max(
        1,
        int(len(text.split()) * 1.3),
    )


def create_embeddings(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    return generate_embeddings(texts)


def split_general_blocks(
    pages: list[dict],
    max_words: int = 180,
) -> list[dict]:
    """
    Fragmentador de respaldo para documentos generales.

    - No depende del tipo o nombre del documento.
    - No intenta adivinar encabezados.
    - Conserva el contenido textual extraído.
    - Evita fragmentos residuales innecesarios.
    - Mantiene las referencias de página.
    - Utiliza solapamiento en páginas con varios chunks.
    """
    if max_words < 40:
        raise ValueError("max_words debe ser al menos 40")

    overlap = min(20, max_words // 8)
    blocks = []
    chunk_number = 1

    for page in pages:
        page_number = page["page_number"]
        text = page.get("text", "")

        if not isinstance(text, str):
            raise ValueError("El texto de la página debe ser una cadena")

        words = text.split()
        total = len(words)

        if total == 0:
            continue

        if total <= max_words:
            groups = [words]
        else:
            # Dividir el texto en grupos equilibrados.
            # El solapamiento se añade entre grupos,
            # sin superar el máximo de palabras.
            effective = max_words - overlap
            number_of_groups = max(
                2,
                (total - overlap + effective - 1) // effective,
            )

            base, extra = divmod(total, number_of_groups)
            groups = []
            offset = 0

            for index in range(number_of_groups):
                group_size = base + (1 if index < extra else 0)
                end = offset + group_size

                start_with_overlap = (
                    max(0, offset - overlap)
                    if index > 0
                    else offset
                )

                group = words[start_with_overlap:end]

                if len(group) > max_words:
                    raise ValueError(
                        "La fragmentación excedió max_words"
                    )

                groups.append(group)
                offset = end

        for group in groups:
            content = " ".join(group).strip()

            if not content:
                continue

            blocks.append({
                "numero_chunk": chunk_number,
                "pagina_inicio": page_number,
                "pagina_fin": page_number,
                "seccion": None,
                "subseccion": None,
                "articulo_numero": None,
                "estrategia_chunking": "general_parrafos",
                "content": content,
            })

            chunk_number += 1

    return blocks





def split_normative_with_attachments(
    pages: list[dict],
) -> list[dict]:
    """
    Conserva el fragmentador normativo, pero evita
    incorporar circulares y resoluciones posteriores
    al contenido del último artículo.

    No depende del título ni del nombre del PDF.
    """
    article_pattern = re.compile(
        r"^ART[IÍ]CULO\s+\d+",
        re.IGNORECASE,
    )

    attachment_pattern = re.compile(
        r"^(?:CIRCULAR|RESOLUCI[ÓO]N|ANEXO|"
        r"MEMORANDO|MEMORÁNDUM|COMUNICADO)\b",
        re.IGNORECASE,
    )

    first_article = None

    for index, page in enumerate(pages):
        if any(
            article_pattern.match(line.strip())
            for line in page["text"].splitlines()
        ):
            first_article = index
            break

    if first_article is None:
        return split_general_blocks(pages)

    attachment_start = len(pages)

    for index in range(first_article + 1, len(pages)):
        lines = [
            line.strip()
            for line in pages[index]["text"].splitlines()
            if line.strip()
        ]

        contains_article = any(
            article_pattern.match(line)
            for line in lines
        )

        contains_attachment = any(
            attachment_pattern.match(line)
            for line in lines[:25]
        )

        if contains_attachment and not contains_article:
            attachment_start = index
            break

    introduction = split_general_blocks(
        pages[:first_article]
    )

    normative = split_normative_blocks(
        pages[first_article:attachment_start]
    )

    attachments = split_general_blocks(
        pages[attachment_start:]
    )

    return introduction + normative + attachments


def preparar_chunks(file_path: str | Path, chunking_mode: str = "auto") -> tuple[str, list[dict]]:
    """Pipeline único de extracción, OCR, segmentación y embeddings, sin persistencia."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {file_path}"
        )

    file_hash = calculate_file_hash(path)
    pages = extract_text_by_page_hybrid(path)

    pages = normalize_page_text_content(pages)
    pages = normalize_pages_text(pages)

    # Seleccionar estrategia según la estructura documental.
    mode = chunking_mode

    if mode == "auto":
        lines = [
            line.strip()
            for page in pages
            for line in page["text"].splitlines()
        ]

        if any(
            re.match(
                r"^ART[IÍ]CULO\s+\d+[°º]?",
                line,
                re.I,
            )
            for line in lines
        ):
            mode = "normativo"

        elif any(
            re.match(r"^[A-Z]\.\s+", line)
            for line in lines
        ) and any(
            re.match(r"^\d+\.\s+", line)
            for line in lines
        ):
            mode = "lineamiento"

        else:
            mode = "general"

    if mode == "faq":
        blocks = split_faq_blocks(pages)

    elif mode == "lineamiento":
        blocks = split_lineamiento_blocks(pages)

    elif mode == "normativo":
        blocks = split_normative_with_attachments(pages)

    else:
        blocks = split_general_blocks(pages)

    # Evitar descartar documentos con texto válido.
    if not blocks and any(
        page["text"].strip()
        for page in pages
    ):
        blocks = split_general_blocks(pages)

    # No perder páginas con texto cuando una estrategia
    # estructural no reconoce sus encabezados.
    covered_pages = set()

    for block in blocks:
        covered_pages.update(
            range(
                block["pagina_inicio"],
                block["pagina_fin"] + 1,
            )
        )

    missing_pages = [
        page
        for page in pages
        if page["page_number"] not in covered_pages
        and useful_characters(page["text"]) >= 35
    ]

    if missing_pages:
        blocks.extend(
            split_general_blocks(missing_pages)
        )

        logger.info(
            "[RAG][PDF] paginas_recuperadas_general=%s",
            len(missing_pages),
        )

    blocks.sort(
        key=lambda block: (
            block["pagina_inicio"],
            block["pagina_fin"],
        )
    )

    valid_blocks = [
        block
        for block in blocks
        if block["content"].strip()
    ]

    contents = [
        block["content"]
        for block in valid_blocks
    ]

    if not valid_blocks:
        raise ValueError("El PDF no contiene texto suficiente para generar fragmentos.")

    embeddings = create_embeddings(contents)
    if len(embeddings) != len(valid_blocks) or any(len(e) != 512 for e in embeddings):
        raise ValueError("Los embeddings deben corresponder a todos los fragmentos y tener dimensión 512.")
    chunks = [dict(
        contenido=block["content"], numero_chunk=index,
        pagina_inicio=block["pagina_inicio"], pagina_fin=block["pagina_fin"],
        seccion=block["seccion"], subseccion=block["subseccion"],
        articulo_numero=block["articulo_numero"], estrategia_chunking=block["estrategia_chunking"],
        tokens_aproximados=estimate_tokens(block["content"]), embedding=embedding, activo=True,
    ) for index, (block, embedding) in enumerate(zip(valid_blocks, embeddings), 1)]
    return file_hash, chunks
