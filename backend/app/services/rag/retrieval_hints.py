from __future__ import annotations


def get_retrieval_hints(
    query_type: str,
    question: str = "",
) -> dict[str, list[str]]:
    q = question.lower().strip()

    hints: dict[str, list[str]] = {
        "keywords": [],
        "section_boost_terms": [],
        "negative_terms": [],
        "stage_terms": [],
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
            "definición",
            "consiste",
            "modalidad",
            "significa",
            "se refiere",
        ]

    elif query_type == "procedure":
        hints["keywords"] = [
            "solicitar",
            "tramitar",
            "requisitos",
            "presentar",
            "adjuntar",
            "procedimiento",
            "pasos",
            "solicitud",
        ]

        hints["section_boost_terms"] = [
            "requisitos",
            "procedimiento",
            "solicitud",
            "trámite",
            "tramite",
        ]

        # Etapa inicial del trámite.
        if any(
            term in q
            for term in [
                "iniciar",
                "inicio",
                "comenzar",
                "primero",
                "qué necesito",
                "que necesito",
                "qué debo presentar primero",
                "que debo presentar primero",
            ]
        ):
            hints["stage_terms"] = [
                "propuesta",
                "solicitud",
                "presentar",
                "aprobada",
                "aprobación",
                "director",
                "tutor",
                "convenio",
                "inicio",
            ]

            hints["negative_terms"] = [
                "memoria final",
                "defensa",
                "tribunal de defensa",
                "informe final",
            ]

        # Etapa de desarrollo.
        elif any(
            term in q
            for term in [
                "durante",
                "avance",
                "desarrollo",
                "seguimiento",
                "mientras realizo",
            ]
        ):
            hints["stage_terms"] = [
                "avance",
                "informe",
                "seguimiento",
                "tutor",
                "desarrollo",
            ]

        # Etapa final.
        elif any(
            term in q
            for term in [
                "finalizar",
                "final",
                "culminar",
                "terminar",
                "al finalizar",
                "defensa",
                "defender",
            ]
        ):
            hints["stage_terms"] = [
                "memoria",
                "defensa",
                "tribunal",
                "conformidad",
                "presentar",
                "final",
            ]

            hints["negative_terms"] = [
                "propuesta inicial",
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
            "consecuencia",
        ]

        hints["section_boost_terms"] = [
            "reprobación",
            "reprobacion",
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