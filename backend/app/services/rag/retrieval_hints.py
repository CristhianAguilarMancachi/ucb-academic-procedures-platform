from __future__ import annotations


def get_retrieval_hints(query_type: str) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {
        "keywords": [],
        "section_boost_terms": [],
        "negative_terms": [],
    }

    if query_type == "factoid":
        hints["keywords"] = [
            "nota mínima",
            "aprobación",
            "cantidad",
            "horas",
            "talleres",
            "cursos",
            "plazo",
            "correo",
            "requisito",
        ]

    elif query_type == "definition":
        hints["keywords"] = [
            "es",
            "consiste",
            "modalidad",
            "definición",
            "significa",
        ]

    elif query_type == "procedure":
        hints["keywords"] = [
            "solicitar",
            "tramitar",
            "requisitos",
            "presentar",
            "adjuntar",
            "debe",
            "deberá",
            "procedimiento",
            "pasos",
        ]
        hints["section_boost_terms"] = [
            "requisitos",
            "procedimiento",
            "solicitud",
            "trámite",
            "tramite",
        ]

    elif query_type == "consequence":
        hints["keywords"] = [
            "reprueba",
            "reprobación",
            "reprobacion",
            "repruebo",
            "qué pasa",
            "que pasa",
            "no existe otra oportunidad",
            "segunda instancia",
            "volver a cursar",
        ]
        hints["section_boost_terms"] = [
            "reprobación",
            "reprobacion",
            "consecuencia",
            "segunda instancia",
            "otra oportunidad",
        ]

    elif query_type == "eligibility":
        hints["keywords"] = [
            "puede",
            "podrá",
            "podra",
            "es posible",
            "se permite",
            "no podrá",
            "no podra",
            "inhabilitación",
            "inhabilitacion",
            "reprobaciones",
        ]
        hints["section_boost_terms"] = [
            "puede",
            "podrá",
            "podra",
            "no podrá",
            "no podra",
            "reprobaciones",
            "inhabilitaciones",
        ]

    elif query_type == "comparison":
        hints["keywords"] = [
            "diferencia",
            "comparación",
            "comparacion",
            "frente a",
            "versus",
        ]

    elif query_type == "contact":
        hints["keywords"] = [
            "correo",
            "contacto",
            "email",
            "mail",
            "@",
        ]

    return hints