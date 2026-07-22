import requests

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def generate_answer(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    prompt = f"""
Eres un asistente académico de la Universidad Católica Boliviana “San Pablo”.

Debes responder únicamente con base en la información proporcionada en el contexto.
No inventes información.
No agregues suposiciones.
No contradigas el contexto.

Reglas de respuesta:
1. Si el contexto contiene una respuesta directa y explícita, respóndela de forma directa.
2. Si el contexto contiene un dato puntual (por ejemplo: número, fecha, nota mínima, cantidad, requisito, correo, plazo), responde ese dato sin decir que falta información.
3. Solo di "No se encontró información suficiente en los documentos cargados." si el contexto realmente no contiene la respuesta.
4. No digas que falta información si el contexto sí contiene la respuesta aunque sea en una sola frase.
5. Responde en español claro, breve y preciso.
6. No cites artículos, páginas, capítulos ni numeraciones normativas dentro del texto de respuesta, porque las fuentes se mostrarán aparte.
7. No empieces respuestas con frases como "Según el artículo", "De acuerdo con el artículo", "Conforme al reglamento" o similares.
8. Responde de forma natural y directa, usando la información normativa solo como respaldo.
9. Si el contexto contiene una definición, devuelve la definición directamente sin introducirla con referencias normativas.
10. Si la pregunta está mal redactada pero el contexto permite inferir la intención con suficiente seguridad, responde normalmente.
11. Si la pregunta es demasiado ambigua y el contexto no permite resolverla, responde: "No se encontró información suficiente en los documentos cargados."

Pregunta:
{question}

Contexto:
{context}
"""

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        },
        timeout=120
    )

    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()