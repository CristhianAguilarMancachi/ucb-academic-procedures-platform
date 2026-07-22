def detect_allowed_documents(question: str) -> list[str] | None:
    q = question.lower()

    topic_map = {
        "Consultas académicas frecuentes": [
            "beca", "becas", "posgrado", "posgrados", "exterior",
            "retiro", "retiros", "abandono", "abandonos",
            "excelencia", "inhabilitaciones"
        ],
        "Lineamientos para la Implementación de los Cursos y Talleres de Formación Integral": [
            "formación integral", "formacion integral",
            "taller", "talleres",
            "curso", "cursos",
            "horas académicas", "horas academicas",
            "power skills", "cultura y arte", "deporte", "habilidades tecnológicas", "habilidades tecnologicas"
        ],
        "Reglamento de Evaluacion del Aprendizaje": [
            "prueba de suficiencia", "suficiencia",
            "evaluación", "evaluacion",
            "nota", "notas",
            "habilitación", "habilitacion",
            "segunda instancia", "reposición", "reposicion",
            "asignatura", "calificación", "calificacion"
        ],
        "Reglamento General de Modalidades de Graduacion": [
            "modalidad de graduación", "modalidad de graduacion",
            "graduación", "graduacion",
            "tesis", "proyecto de grado", "trabajo dirigido",
            "examen de grado", "modalidades de graduación", "modalidades de graduacion"
        ],
    }

    scores = {}

    for document, keywords in topic_map.items():
        score = sum(1 for keyword in keywords if keyword in q)
        if score > 0:
            scores[document] = score

    if not scores:
        return None

    best_score = max(scores.values())
    best_documents = [doc for doc, score in scores.items() if score == best_score]

    return best_documents