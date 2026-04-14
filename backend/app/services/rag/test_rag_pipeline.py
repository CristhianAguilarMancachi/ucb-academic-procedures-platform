from app.services.rag.retriever import retrieve_relevant_chunks
from app.services.rag.prompt_builder import build_rag_prompt
from app.services.rag.generator import generate_response


if __name__ == "__main__":
    question = "¿Cuáles son los requisitos para obtener el Diploma Académico?"

    results = retrieve_relevant_chunks(question)

    documents = results.get("documents", [[]])[0][:2]
    metadatas = results.get("metadatas", [[]])[0][:2]

    prompt = build_rag_prompt(question, documents, metadatas)

    print("\n===== PROMPT ENVIADO AL MODELO =====\n")
    print(prompt)

    answer = generate_response(prompt)

    print("\n===== RESPUESTA DEL MODELO =====\n")
    print(answer)