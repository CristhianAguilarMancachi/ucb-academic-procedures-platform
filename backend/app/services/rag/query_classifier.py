from __future__ import annotations

from app.services.rag.llm_client import (
    complete_text,
    LLMUnavailableError,
)


VALID_QUERY_TYPES = {
    "factoid",
    "definition",
    "procedure",
    "consequence",
    "eligibility",
    "comparison",
    "contact",
    "ambiguous",
    "general",
}


KNOWN_ACADEMIC_CONCEPTS = {
    "segunda instancia",
    "prueba de suficiencia",
    "suficiencia",
    "trabajo dirigido",
    "proyecto de grado",
    "tesis",
    "tesis de grado",
    "examen de grado",
    "graduación directa",
    "graduacion directa",
    "graduación por excelencia",
    "graduacion por excelencia",
    "modalidad de graduación",
    "modalidad de graduacion",
    "formación integral",
    "formacion integral",
}


def heuristic_query_type(
    question: str,
) -> str | None:
    q = question.lower().strip()

    if not q:
        return "ambiguous"

    if q in KNOWN_ACADEMIC_CONCEPTS:
        return "definition"

    if any(
        token in q
        for token in [
            "diferencia",
            "diferencias",
            "comparar",
            "comparación",
            "comparacion",
            "en qué se diferencia",
            "en que se diferencia",
            "mejor que",
            "igual que",
            "versus",
            " vs ",
        ]
    ):
        return "comparison"

    if any(
        token in q
        for token in [
            "correo",
            "mail",
            "email",
            "contacto",
        ]
    ):
        return "contact"

    if any(
        token in q
        for token in [
            "qué es",
            "que es",
            "en qué consiste",
            "en que consiste",
            "qué significa",
            "que significa",
            "definición",
            "definicion",
        ]
    ):
        return "definition"

    if any(
        token in q
        for token in [
            "qué pasa si",
            "que pasa si",
            "qué ocurre si",
            "que ocurre si",
            "qué sucede si",
            "que sucede si",
            "repruebo",
            "reprueba",
            "reprobé",
            "reprobe",
        ]
    ):
        return "consequence"

    if any(
        token in q
        for token in [
            "puedo",
            "puede",
            "es posible",
            "se puede",
            "podria",
            "podría",
            "llego con",
            "alcanzar",
            "aprobar con",
            "cumplo",
            "cumple",
        ]
    ):
        return "eligibility"

    if any(
        token in q
        for token in [
            "cómo",
            "como",
            "qué debo hacer",
            "que debo hacer",
            "qué tengo que hacer",
            "que tengo que hacer",
            "qué necesito",
            "que necesito",
            "qué necesito para",
            "que necesito para",
            "requisitos",
            "solicitar",
            "tramitar",
            "procedimiento",
            "pasos",
            "iniciar",
            "presentar",
            "adjuntar",
        ]
    ):
        return "procedure"

    if any(
        token in q
        for token in [
            "cuánto",
            "cuanto",
            "cuántas",
            "cuantas",
            "cuántos",
            "cuantos",
            "qué nota",
            "que nota",
            "qué plazo",
            "que plazo",
            "cuál es la nota",
            "cual es la nota",
        ]
    ):
        return "factoid"

    return None


def extract_label(
    raw_text: str,
) -> str:
    text = raw_text.strip().lower()

    if text in VALID_QUERY_TYPES:
        return text

    lines = [
        line.strip().lower()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:
        if line in VALID_QUERY_TYPES:
            return line

    return "general"


def classify_query(
    question: str,
) -> str:
    heuristic = heuristic_query_type(
        question
    )

    if heuristic is not None:
        return heuristic

    prompt = f"""
Clasifica la consulta del usuario en exactamente una categoría.

Categorías permitidas:
- factoid
- definition
- procedure
- consequence
- eligibility
- comparison
- contact
- ambiguous
- general

Criterios:

factoid:
Solicita un dato puntual como nota, cantidad,
plazo, número, fecha o requisito específico.

definition:
Pregunta qué es algo, qué significa o en qué consiste.

procedure:
Pregunta qué debe hacer el usuario, cómo realizar un trámite,
qué pasos seguir o qué requisitos presentar.

consequence:
Pregunta qué sucede como consecuencia de una acción o situación.

eligibility:
Pregunta si una persona puede hacer algo
o si cumple una condición.

comparison:
Solicita diferencias o comparación entre dos o más conceptos,
procesos, modalidades o situaciones.

contact:
Solicita un correo, contacto, persona o unidad
a la cual dirigirse.

ambiguous:
La consulta no permite determinar razonablemente
qué tema, trámite, modalidad o situación está preguntando.

general:
Consulta académica comprensible que no encaja claramente
en ninguna categoría anterior.

Devuelve únicamente una palabra de la lista.
No agregues explicaciones.

Consulta:
{question}
""".strip()

    try:
        result = complete_text(
            prompt,
            temperature=0.0,
            max_completion_tokens=32,
            reasoning_effort="low",
            task="classification",
        )

        return extract_label(
            result
        )

    except LLMUnavailableError:
        # La clasificación es auxiliar.
        # Si falla, no debe bloquear toda la consulta.
        return "general"