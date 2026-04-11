from app.services.rag.retriever import retrieve_relevant_chunks


if __name__ == "__main__":
    question = "¿Cuáles son los requisitos para obtener el Diploma Académico?"
    results = retrieve_relevant_chunks(question)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        print(f"\n--- Resultado {i} ---")
        print(f"Fuente: {meta}")
        print(f"Contenido:\n{doc}")