TRAMITES_CATALOG = [
    {
        "id": "reglamento_titulos_grados",
        "label": "Reglamento de Títulos y Grados",
        "document_names": ["04_Reglamento_Titulos_y_Grados.pdf"],
    }
]


def get_tramites_catalog() -> list[dict]:
    return TRAMITES_CATALOG


def get_tramite_by_id(tramite_id: str) -> dict | None:
    for tramite in TRAMITES_CATALOG:
        if tramite["id"] == tramite_id:
            return tramite
    return None