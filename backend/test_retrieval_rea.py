from app.db.session import SessionLocal
from app.services.rag.retriever import retrieve_relevant_chunks

db = SessionLocal()

queries = [
    "¿Qué es la prueba de suficiencia?",
    "¿Cuál es la nota mínima de aprobación en la prueba de suficiencia?",
    "¿Qué pasa si un estudiante no se habilita a la evaluación final?",
    "¿Cuántas oportunidades hay para aprobar la evaluación final?",
    "¿Qué es la evaluación continua?"
]

try:
    for query in queries:
        documents, metadatas = retrieve_relevant_chunks(db=db, query=query)

        print("=" * 80)
        print("PREGUNTA:")
        print(query)
        print("=" * 80)

        for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
            print(f"\nRESULTADO {i}")
            print("-" * 80)
            print("METADATA:", meta)
            print("CONTENIDO:")
            print(doc[:1200])
        print("\n\n")
finally:
    db.close()