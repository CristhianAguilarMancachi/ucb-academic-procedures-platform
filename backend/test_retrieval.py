from app.db.session import SessionLocal
from app.services.rag.retriever import retrieve_relevant_chunks

db = SessionLocal()

try:
    query = "¿Cuántas horas de formación integral debe cumplir un estudiante?"
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
        print(doc[:1500])
finally:
    db.close()