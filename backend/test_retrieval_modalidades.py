from app.db.session import SessionLocal
from app.services.rag.pipeline import run_rag_pipeline

db = SessionLocal()

queries = [
    "¿Qué modalidades de graduación existen?",
    "¿Qué es la graduación por excelencia?",
    "¿Qué modalidades corresponden al nivel de licenciatura?",
    "¿Qué modalidades corresponden al Técnico Universitario Superior?",
    "¿Qué es la pasantía como modalidad de graduación?",
    "¿Qué es el proyecto de grado técnico?",
    "¿Qué es el trabajo dirigido?",
    "¿Qué es el examen de grado?"
]

try:
    for query in queries:
        result = run_rag_pipeline(db=db, question=query)

        print("=" * 100)
        print("PREGUNTA:")
        print(query)
        print("-" * 100)
        print("RESPUESTA:")
        print(result["answer"])
        print("-" * 100)
        print("FUENTES:")
        for source in result["sources"]:
            print(source)
        print()
finally:
    db.close()