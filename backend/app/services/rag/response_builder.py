from typing import Any


def build_structured_response(
    answer_type: str,
    answer_text: str,
    grounded: bool = True
) -> dict[str, Any]:
    return {
        "answer_type": answer_type,
        "answer_text": answer_text.strip(),
        "grounded": grounded,
    }


def render_response(structured_response: dict[str, Any]) -> str:
    answer_type = structured_response.get("answer_type", "general")
    answer_text = structured_response.get("answer_text", "").strip()
    grounded = structured_response.get("grounded", True)

    if not answer_text:
        return "No se encontró información suficiente en los documentos cargados."

    if not grounded:
        return "No se encontró información suficiente en los documentos cargados."

    if answer_type in {"quantity", "definition", "contact", "consequence", "possibility"}:
        return answer_text

    if answer_type == "list_modalities":
        return answer_text

    return answer_text