from __future__ import annotations

import re
import unicodedata


DOCUMENT_FAQ = (
    "Consultas académicas frecuentes"
)

DOCUMENT_FORMACION_INTEGRAL = (
    "Lineamientos para la Implementación de los Cursos y Talleres "
    "de Formación Integral"
)

DOCUMENT_EVALUACION = (
    "Reglamento de Evaluacion del Aprendizaje"
)

DOCUMENT_GRADUACION = (
    "Reglamento General de Modalidades de Graduacion"
)


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_question(
    question: str,
) -> str:
    """
    Normaliza una pregunta para routing.

    Se conserva una versión sin tildes para evitar tener
    que duplicar todas las variantes en las reglas.
    """

    text = (
        question
        .lower()
        .strip()
    )

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        character
        for character in text
        if unicodedata.category(
            character
        )
        != "Mn"
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# ============================================================
# COINCIDENCIAS
# ============================================================

def contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """
    Comprueba una frase completa.

    Evita errores como:

        habilitacion
            dentro de
        inhabilitaciones

    porque se usan límites de palabra.
    """

    normalized_phrase = (
        normalize_question(
            phrase,
        )
    )

    pattern = (
        r"(?<!\w)"
        + re.escape(
            normalized_phrase,
        )
        + r"(?!\w)"
    )

    return (
        re.search(
            pattern,
            text,
        )
        is not None
    )


def contains_any(
    text: str,
    terms: list[str],
) -> bool:
    return any(
        contains_phrase(
            text,
            term,
        )
        for term in terms
    )


def contains_all(
    text: str,
    terms: list[str],
) -> bool:
    return all(
        contains_phrase(
            text,
            term,
        )
        for term in terms
    )


# ============================================================
# ROUTING ESPECÍFICO
# ============================================================

def detect_exact_topic_documents(
    question: str,
) -> list[str] | None:
    """
    Detecta situaciones suficientemente específicas
    como para restringir la búsqueda a uno o varios
    documentos institucionales concretos.

    Las reglas más específicas deben ejecutarse antes
    que las reglas generales.
    """

    q = normalize_question(
        question,
    )


    # --------------------------------------------------------
    # EXCELENCIA + INHABILITACIONES
    # --------------------------------------------------------
    #
    # Este caso está explicado explícitamente en
    # "Consultas académicas frecuentes".
    #
    # No debe enviarse al Reglamento de Evaluación solo
    # porque aparezca una palabra relacionada con
    # "habilitación".
    # --------------------------------------------------------

    if (
        contains_phrase(
            q,
            "excelencia",
        )
        and (
            contains_phrase(
                q,
                "inhabilitacion",
            )
            or contains_phrase(
                q,
                "inhabilitaciones",
            )
            or contains_phrase(
                q,
                "inhabilitado",
            )
            or contains_phrase(
                q,
                "inhabilitada",
            )
        )
    ):
        return [
            DOCUMENT_FAQ,
        ]


    # --------------------------------------------------------
    # CONSULTAS ACADÉMICAS FRECUENTES
    # --------------------------------------------------------

    if contains_any(
        q,
        [
            "abandono parcial",
            "abandono total",
            "retiro de una asignatura",
            "retiro de asignatura",
            "retiro de materia",
            "abandono de una asignatura",
            "abandono de asignatura",
            "abandono de materia",
        ],
    ):
        return [
            DOCUMENT_FAQ,
        ]


    if (
        contains_phrase(
            q,
            "retiro",
        )
        and contains_phrase(
            q,
            "abandono",
        )
    ):
        return [
            DOCUMENT_FAQ,
        ]


    if contains_any(
        q,
        [
            "posgrado en el exterior",
            "posgrados en el exterior",
            "beca en el exterior",
            "becas en el exterior",
            "documentos especiales",
        ],
    ):
        return [
            DOCUMENT_FAQ,
        ]


    # --------------------------------------------------------
    # FORMACIÓN INTEGRAL
    # --------------------------------------------------------

    if contains_any(
        q,
        [
            "formacion integral",
            "power skills",
            "cultura y arte",
            "cuidado del cuerpo",
            "habilidades tecnologicas",
        ],
    ):
        return [
            DOCUMENT_FORMACION_INTEGRAL,
        ]


    # --------------------------------------------------------
    # EVALUACIÓN DEL APRENDIZAJE
    # --------------------------------------------------------

    if contains_any(
        q,
        [
            "prueba de suficiencia",
            "segunda instancia",
            "evaluacion final",
        ],
    ):
        return [
            DOCUMENT_EVALUACION,
        ]


    # --------------------------------------------------------
    # MODALIDADES DE GRADUACIÓN
    # --------------------------------------------------------

    if contains_any(
        q,
        [
            "trabajo dirigido",
            "proyecto de grado",
            "tesis de grado",
            "tesis",
            "examen de grado",
            "graduacion por excelencia",
            "modalidad de graduacion",
            "modalidades de graduacion",
        ],
    ):
        return [
            DOCUMENT_GRADUACION,
        ]


    return None


# ============================================================
# ROUTING GENERAL
# ============================================================

def detect_allowed_documents(
    question: str,
) -> list[str] | None:
    q = normalize_question(
        question,
    )


    # ========================================================
    # 1. REGLAS ESPECÍFICAS
    # ========================================================

    exact_documents = (
        detect_exact_topic_documents(
            q,
        )
    )

    if exact_documents:
        return exact_documents


    # ========================================================
    # 2. ROUTING GENERAL
    # ========================================================

    topic_map: dict[
        str,
        list[str],
    ] = {

        DOCUMENT_FAQ: [
            "beca",
            "becas",
            "posgrado",
            "posgrados",
            "exterior",
            "retiro",
            "retiros",
            "abandono",
            "abandonos",
            "analista academica",
            "excelencia",
            "inhabilitacion",
            "inhabilitaciones",
        ],


        DOCUMENT_FORMACION_INTEGRAL: [
            "formacion integral",
            "taller integral",
            "talleres integrales",
            "curso integral",
            "cursos integrales",
            "horas academicas",
            "power skills",
            "cultura y arte",
            "deporte",
            "habilidades tecnologicas",
        ],


        DOCUMENT_EVALUACION: [
            "prueba de suficiencia",
            "suficiencia",
            "evaluacion",
            "nota",
            "notas",
            "habilitacion",
            "segunda instancia",
            "reposicion",
            "calificacion",
            "kardex",
        ],


        DOCUMENT_GRADUACION: [
            "modalidad de graduacion",
            "modalidades de graduacion",
            "graduacion",
            "tesis",
            "proyecto de grado",
            "trabajo dirigido",
            "examen de grado",
            "defensa",
            "memoria",
            "tribunal",
        ],
    }


    scores: dict[
        str,
        int,
    ] = {}


    for (
        document,
        keywords,
    ) in topic_map.items():

        score = 0


        for keyword in keywords:

            if contains_phrase(
                q,
                keyword,
            ):
                score += 1


        if score > 0:
            scores[
                document
            ] = score


    if not scores:
        return None


    best_score = max(
        scores.values(),
    )


    best_documents = [
        document
        for (
            document,
            score,
        )
        in scores.items()
        if score
        ==
        best_score
    ]


    return best_documents