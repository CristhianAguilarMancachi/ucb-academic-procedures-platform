import hashlib
import re
import unicodedata
from pathlib import Path

import fitz
import pytesseract
from pdf2image import convert_from_path

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


def extract_text_by_page_with_ocr(
    file_path: str | Path,
) -> list[dict]:
    path = Path(file_path)

    images = convert_from_path(
        str(path),
        dpi=300,
    )

    pages = []

    for page_index, image in enumerate(
        images,
        start=1,
    ):
        try:
            text = pytesseract.image_to_string(
                image,
                lang="spa",
                config="--psm 6",
            )
        except Exception:
            text = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--psm 6",
            )

        pages.append(
            {
                "page_number": page_index,
                "text": text.strip(),
            }
        )

    return pages


def clean_page_lines(
    lines: list[str],
) -> list[str]:
    cleaned = []

    skip_patterns = [
        "UNIVERSIDAD CATÓLICA BOLIVIANA",
        "PABLO”",
        "Versión",
        "Vigencia",
        "Nº Página",
        "LINEAMIENTOS PARA LA IMPLEMENTACIÓN",
        "DE LOS CURSOS Y TALLERES DE FORMACIÓN",
        "INTEGRAL",
        "REGLAMENTO GENERAL DE MODALIDADES DE GRADUACIÓN",
    ]

    for line in lines:
        normalized = " ".join(
            line.split()
        ).strip()

        if not normalized:
            continue

        if normalized in {
            "1",
            "2",
            "3",
            "4",
        }:
            continue

        if normalized.startswith("Jun.-2025"):
            continue

        if re.fullmatch(
            r"Página \d+ de \d+",
            normalized,
            flags=re.IGNORECASE,
        ):
            continue

        if any(
            pattern in normalized
            for pattern in skip_patterns
        ):
            continue

        cleaned.append(normalized)

    return cleaned


def normalize_ocr_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    replacements = {
        "evaluacibn": "evaluación",
        "informacibn": "información",
        "habilitacibn": "habilitación",
        "reposicibn": "reposición",
        "calificacibn": "calificación",
        "Direccidn": "Dirección",
        "direction": "dirección",
        "reprobation": "reprobación",
        "option": "opción",
        "formacibn": "formación",
        "contribution": "contribución",
        "formative": "formativo",
        "Académico Administrativa": (
            "Académico Administrativa"
        ),
        "Io": "lo",
        "tai": "tal",
        "motive": "motivo",
        "deformación": "de formación",
        "cursarla asignatura": "cursar la asignatura",
        "Debera": "Deberá",
        "debera": "deberá",
        "Evaluacion": "Evaluación",
        "evaluacion": "evaluación",
        "Titulo": "Título",
        "titulo": "título",
        "Modalidades de Graduacion": (
            "Modalidades de Graduación"
        ),
        "Graduacion": "Graduación",
        "graduacion": "graduación",
        "Monografia": "Monografía",
        "Pasantia": "Pasantía",
        "Tecnico": "Técnico",
        "tecnico": "técnico",
        "Universitario Superior": (
            "Universitario Superior"
        ),
        "Via Diplomado": "Vía Diplomado",
        "via diplomado": "vía diplomado",
    }

    for wrong, right in replacements.items():
        text = text.replace(
            wrong,
            right,
        )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = re.sub(
        r"\n?\s*[%£§¢¬]+\s*\n?",
        "\n",
        text,
    )

    text = re.sub(
        r"\n?\s*\d+\s*S\s*[’']\s*\n?",
        "\n",
        text,
    )

    text = re.sub(
        r"\n?\s*Pagina\s+\d+\s+de\s+\d+\s*\n?",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"REGLAMENTO GENERAL DE MODALIDADES "
        r"DE GRADUACI[OÓ]N",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"UNIVERSIDAD CAT[OÓ]LICA BOLIVIANA"
        r".*?SAN PABLO",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s+([,.;:])",
        r"\1",
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


def preparar_chunks(file_path: str | Path, chunking_mode: str = "normativo") -> tuple[str, list[dict]]:
    """Pipeline único de extracción, OCR, segmentación y embeddings, sin persistencia."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {file_path}"
        )

    file_hash = calculate_file_hash(path)
    pages = extract_text_by_page(path)

    if not has_meaningful_text(pages):
        print(
            f"[INFO] No se encontró texto suficiente "
            f"en {path.name}. Aplicando OCR..."
        )

        pages = extract_text_by_page_with_ocr(path)

    pages = normalize_page_text_content(pages)
    pages = normalize_pages_text(pages)

    if chunking_mode == "faq":
        blocks = split_faq_blocks(pages)
    elif chunking_mode == "lineamiento":
        blocks = split_lineamiento_blocks(pages)
    else:
        blocks = split_normative_blocks(pages)

    valid_blocks = [
        block
        for block in blocks
        if block["content"].strip()
    ]

    contents = [
        block["content"]
        for block in valid_blocks
    ]

    embeddings = create_embeddings(contents)

    if not valid_blocks:
        raise ValueError("El PDF no contiene texto suficiente para generar fragmentos.")
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
