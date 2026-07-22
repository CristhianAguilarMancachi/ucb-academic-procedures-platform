import re

from app.services.rag.response_builder import build_structured_response


def detect_answer_intent(question: str) -> str:
    q = question.lower()

    if (
        "qué pasa si" in q
        or "que pasa si" in q
        or "qué ocurre si" in q
        or "que ocurre si" in q
        or "qué sucede si" in q
        or "que sucede si" in q
    ):
        return "consequence"

    if "qué modalidades" in q or "que modalidades" in q:
        return "list_modalities"

    if "puede" in q or "se puede" in q or "es posible" in q:
        return "possibility"

    if "correo" in q or "contact" in q or "beca" in q or "posgrado" in q or "exterior" in q:
        return "contact"

    return "general"


def try_intent_based_answer(question: str, documents: list[str]) -> dict | None:
    q = question.lower()
    intent = detect_answer_intent(question)
    combined = "\n".join(documents)

    if intent == "consequence":
        consequence_patterns = [
            r"no habilitaci[oó]n a la evaluaci[oó]n final significa que el estudiante deber[aá] volver a cursar la asignatura",
            r"deber[aá]\s+volver\s+a\s+cursar\s+la\s+asignatura",
            r"equivale\s+a\s+la\s+reprobaci[oó]n\s+de\s+la\s+asignatura",
        ]

        for pattern in consequence_patterns:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                sentence = match.group(0).strip()
                sentence = re.sub(r"\s+", " ", sentence)
                sentence = sentence[0].upper() + sentence[1:]
                if not sentence.endswith("."):
                    sentence += "."
                return build_structured_response(
                    answer_type="consequence",
                    answer_text=sentence,
                    grounded=True
                )

    if intent == "possibility":
        if "excelencia" in q and "inhabilit" in q:
            if "inhabilitaciones cuentan como reprobaciones" in combined.lower():
                return build_structured_response(
                    answer_type="possibility",
                    answer_text="No. Un estudiante no puede postular por excelencia si tiene inhabilitaciones, porque estas cuentan como reprobaciones.",
                    grounded=True
                )

    if intent == "list_modalities":
        modalities = []

        patterns = [
            r"graduaci[oó]n directa",
            r"monograf[ií]a",
            r"proyecto de grado t[eé]cnico",
            r"pasant[ií]a",
            r"tesis de grado",
            r"proyecto de grado",
            r"trabajo dirigido",
            r"examen de grado",
            r"graduaci[oó]n por excelencia",
            r"graduaci[oó]n v[ií]a diplomado",
            r"internado rotatorio",
        ]

        lowered = combined.lower()
        seen = set()

        for pattern in patterns:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match:
                item = match.group(0).strip()
                item = re.sub(r"\s+", " ", item)

                replacements = {
                    "graduacion directa": "Graduación Directa",
                    "monografia": "Monografía",
                    "proyecto de grado técnico": "Proyecto de Grado Técnico",
                    "pasantia": "Pasantía",
                    "tesis de grado": "Tesis de Grado",
                    "proyecto de grado": "Proyecto de Grado",
                    "trabajo dirigido": "Trabajo Dirigido",
                    "examen de grado": "Examen de Grado",
                    "graduacion por excelencia": "Graduación por Excelencia",
                    "graduación por excelencia": "Graduación por Excelencia",
                    "graduacion vía diplomado": "Graduación Vía Diplomado",
                    "graduación vía diplomado": "Graduación Vía Diplomado",
                    "graduacion via diplomado": "Graduación Vía Diplomado",
                    "graduación via diplomado": "Graduación Vía Diplomado",
                    "internado rotatorio": "Internado Rotatorio",
                }

                normalized_item = replacements.get(item.lower(), item.title())

                if normalized_item not in seen:
                    seen.add(normalized_item)
                    modalities.append(normalized_item)

        if modalities:
            answer = "Las modalidades de graduación identificadas en los documentos son:\n\n"
            for idx, item in enumerate(modalities, start=1):
                answer += f"{idx}. {item}\n"

            return build_structured_response(
                answer_type="list_modalities",
                answer_text=answer.strip(),
                grounded=True
            )

    return None