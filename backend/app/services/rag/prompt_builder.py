def build_rag_prompt(question: str, documents: list[str], metadatas: list[dict]) -> str:
    context_blocks = []

    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        source = meta.get("source", "desconocido")
        page = meta.get("page", "N/A")

        context_blocks.append(
            f"[Fuente {i} | Documento: {source} | Página: {page}]\n{doc}"
        )

    context_text = "\n\n".join(context_blocks)

    prompt = f"""
Responde únicamente con base en el contexto proporcionado.
Si la información no está en el contexto, indícalo claramente.
No inventes requisitos, pasos, plazos ni condiciones.
Si existen varios requisitos, enuméralos claramente.
Al final, menciona brevemente las fuentes utilizadas.

Pregunta:
{question}

Contexto:
{context_text}
""".strip()

    return prompt