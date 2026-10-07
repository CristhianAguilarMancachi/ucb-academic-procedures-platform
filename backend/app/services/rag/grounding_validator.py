from __future__ import annotations

import re

from app.services.rag.llm_client import (
    LLMUnavailableError,
    complete_text,
)
from app.services.rag.prompt_builder import (
    NO_INFORMATION_MESSAGE,
)


GROUNDING_MAX_COMPLETION_TOKENS = 1600


def build_grounding_prompt(
    question: str,
    answer: str,
    documents: list[str],
) -> str:
    context = "\n\n---\n\n".join(
        document.strip()
        for document in documents
        if document.strip()
    )

    return f"""
Actúa como un verificador estricto de fidelidad documental.

Debes revisar la RESPUESTA PROPUESTA utilizando únicamente el
CONTEXTO INSTITUCIONAL.

PREGUNTA:
{question}

RESPUESTA PROPUESTA:
{answer}

CONTEXTO INSTITUCIONAL:
{context}

REGLAS OBLIGATORIAS:

1. Revisa cada afirmación de forma independiente.

2. Conserva únicamente afirmaciones cuyo significado esté respaldado
   explícitamente por el contexto.

3. Si una frase mezcla información respaldada con una inferencia,
   conserva únicamente la parte respaldada.

4. No agregues conocimiento externo.

5. No completes procedimientos utilizando acciones administrativas
   habituales.

6. Si el contexto indica:
   "la solicitud se realiza mediante SIAAn",
   conserva ese mismo nivel de detalle.

   No agregues:
   - ingresar al sistema,
   - completar formularios,
   - seleccionar opciones,
   - hacer clic,
   - confirmar,
   salvo que el contexto lo indique expresamente.

7. No expandas siglas o acrónimos si el nombre completo no aparece
   expresamente en el contexto.

8. Si el contexto únicamente indica que un costo depende de la fecha
   de la solicitud, solo puedes afirmar eso.

   NO concluyas que:
   - los montos aparecen en el Calendario académico,
   - las tarifas aparecen en el Calendario académico,
   - existen fechas de cobro publicadas en el Calendario académico,
   - el Calendario contiene una tabla de precios,
   salvo que el contexto lo diga explícitamente.

9. No inventes:
   - requisitos,
   - documentos,
   - pasos,
   - montos,
   - porcentajes,
   - fechas,
   - plazos,
   - autoridades,
   - consecuencias,
   - excepciones,
   - formularios,
   - nombres completos de siglas.

10. Si parte de la pregunta puede responderse y otra parte no:
    conserva la información respaldada y señala específicamente
    qué dato no está disponible.

11. Solo cuando ninguna parte pueda responderse devuelve exactamente:

"{NO_INFORMATION_MESSAGE}"

12. No menciones artículos, páginas, fuentes, chunks ni el proceso
    de validación.

13. No uses Markdown.

14. No agregues información nueva.

15. Ante duda, utiliza siempre la formulación más conservadora.

16. No acortes una respuesta correcta únicamente para hacerla más breve.
    Si la respuesta propuesta contiene varios puntos respaldados, conserva
    todos los puntos necesarios para responder completamente la pregunta.

17. Devuelve una respuesta completa. No termines en mitad de una palabra,
    frase, enumeración o idea.

Devuelve únicamente la respuesta final corregida.

RESPUESTA VALIDADA:
""".strip()


def apply_conservative_guards(
    question: str,
    answer: str,
) -> str:
    q = question.lower()
    result = answer.strip()

    # =========================================================
    # ABANDONO PARCIAL
    # =========================================================

    if "abandono parcial" in q:

        # -----------------------------------------------------
        # No expandir SIAAn
        # -----------------------------------------------------

        result = re.sub(
            (
                r"Sistema\s+Integral\s+de\s+"
                r"Administraci[oó]n\s+Acad[eé]mica"
                r"\s*\(SIAAn\)"
            ),
            "SIAAn",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            (
                r"Sistema\s+de\s+Informaci[oó]n\s+Acad[eé]mica"
                r"\s*\(SIAAn\)"
            ),
            "SIAAn",
            result,
            flags=re.IGNORECASE,
        )

        # -----------------------------------------------------
        # Evitar pasos de interfaz inferidos
        # -----------------------------------------------------

        result = re.sub(
            (
                r"(?:Ingresar|Ingresa)\s+"
                r"(?:al|en el)\s+SIAAn\s+y\s+"
                r"(?:presentar|realizar|completar)\s+"
                r"la\s+solicitud"
            ),
            "Realizar la solicitud mediante el SIAAn",
            result,
            flags=re.IGNORECASE,
        )

        # -----------------------------------------------------
        # Eliminar atribuciones no respaldadas al Calendario
        # -----------------------------------------------------

        calendar_patterns = [
            (
                r"(?:las|los)\s+"
                r"(?:tarifas|montos|costos)\s+"
                r"(?:exactas|exactos|específicos|especificos)?\s*"
                r"(?:están|estan|se encuentran)\s+"
                r"(?:establecidas|establecidos|publicadas|publicados)\s+"
                r"en\s+el\s+Calendario\s+acad[eé]mico"
                r"(?:\s+de\s+cada\s+semestre)?"
            ),
            (
                r"(?:el\s+)?costo\s+"
                r"(?:se\s+determina|se\s+calcula)\s+"
                r"seg[uú]n\s+las\s+fechas\s+de\s+cobro\s+"
                r"que\s+aparecen\s+en\s+el\s+"
                r"Calendario\s+acad[eé]mico"
                r"(?:\s+de\s+cada\s+semestre)?"
            ),
            (
                r"(?:las\s+)?fechas\s+de\s+cobro\s+"
                r"(?:aparecen|están|estan|se encuentran)\s+"
                r"en\s+el\s+Calendario\s+acad[eé]mico"
                r"(?:\s+de\s+cada\s+semestre)?"
            ),
            (
                r"(?:los\s+)?montos\s+"
                r"(?:aparecen|están|estan|se encuentran)\s+"
                r"en\s+el\s+Calendario\s+acad[eé]mico"
                r"(?:\s+de\s+cada\s+semestre)?"
            ),
        ]

        for pattern in calendar_patterns:
            result = re.sub(
                pattern,
                "",
                result,
                flags=re.IGNORECASE,
            )

        # -----------------------------------------------------
        # Preguntas por monto exacto
        # -----------------------------------------------------

        asks_exact_amount = (
            "cuánto cuesta" in q
            or "cuanto cuesta" in q
            or "monto exacto" in q
            or "valor exacto" in q
            or "bolivianos" in q
        )

        if asks_exact_amount:
            lowered_result = result.lower()

            already_mentions_missing_amount = any(
                phrase in lowered_result
                for phrase in [
                    "monto exacto en bolivianos no está",
                    "monto exacto en bolivianos no esta",
                    "valor exacto en bolivianos no está",
                    "valor exacto en bolivianos no esta",
                    "monto exacto no está",
                    "monto exacto no esta",
                    "valor exacto no está",
                    "valor exacto no esta",
                    "no especifica el monto exacto",
                    "no indica el monto exacto",
                    "no está indicado",
                    "no esta indicado",
                    "no se encuentra especificado",
                    "no se encuentra detallado",
                ]
            )

            if (
                "depende de la fecha" in lowered_result
                and not already_mentions_missing_amount
            ):
                result = (
                    result.rstrip(" .")
                    + ". La información disponible no especifica "
                    "el monto exacto en bolivianos."
                )

    # =========================================================
    # RETIRO VS ABANDONO
    # =========================================================

    if (
        "retiro" in q
        and "abandono" in q
    ):
        result = re.sub(
            r"antes de que comience el semestre",
            "dentro del periodo de inscripciones",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"antes del inicio del semestre",
            "dentro del periodo de inscripciones",
            result,
            flags=re.IGNORECASE,
        )

    # =========================================================
    # LIMPIEZA
    # =========================================================

    result = re.sub(
        r"[ \t]+",
        " ",
        result,
    )

    result = re.sub(
        r"\s+\.",
        ".",
        result,
    )

    result = re.sub(
        r"\.\s*\.",
        ".",
        result,
    )

    result = re.sub(
        r";\s*\.",
        ".",
        result,
    )

    result = re.sub(
        r"\s{2,}",
        " ",
        result,
    )

    return result.strip()


def validate_grounded_answer(
    question: str,
    answer: str,
    documents: list[str],
) -> str:
    if not answer.strip():
        return answer

    if not documents:
        return NO_INFORMATION_MESSAGE

    prompt = build_grounding_prompt(
        question=question,
        answer=answer,
        documents=documents,
    )

    validated_answer = answer

    try:
        llm_validated_answer = complete_text(
            prompt,
            temperature=0.0,
            max_completion_tokens=GROUNDING_MAX_COMPLETION_TOKENS,
            reasoning_effort="medium",
            task="grounding",
        )

        if llm_validated_answer.strip():
            validated_answer = (
                llm_validated_answer.strip()
            )

    except LLMUnavailableError:
        validated_answer = answer

    return apply_conservative_guards(
        question=question,
        answer=validated_answer,
    )