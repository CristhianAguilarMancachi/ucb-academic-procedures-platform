def build_rag_prompt(question: str, documents: list[str], metadatas: list[dict]) -> str:
    context_blocks = []

    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        source = meta.get("source", "desconocido")
        page = meta.get("page", "N/A")
        article_number = meta.get("article_number")

        article_text = f" | Artículo: {article_number}" if article_number else ""

        context_blocks.append(
            f"[Fuente {i} | Documento: {source} | Página: {page}{article_text}]\n{doc}"
        )

    context_text = "\n\n".join(context_blocks)

    prompt = f"""
Responde únicamente con base en el contexto proporcionado.

Reglas:
- Responde solo lo que se pregunta.
- No agregues explicaciones extra si no fueron solicitadas.
- No menciones información de otras fuentes si no aporta directamente a la respuesta.
- No inventes requisitos, pasos, plazos ni condiciones.
- Si existen varios elementos, enuméralos claramente.
- No incluyas fuentes, páginas ni referencias al final de la respuesta.
- Devuelve únicamente el contenido de la respuesta final.

Pregunta:
{question}

Contexto:
{context_text}
""".strip()

    return prompt