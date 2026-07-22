from app.db.session import SessionLocal
from app.services.rag.ingest import ingest_document

db = SessionLocal()

try:
    result = ingest_document(
        db=db,
        file_path="/app/data/documents/Reglamento de Evaluacion de Aprendizaje.pdf",
        titulo="Reglamento de Evaluacion del Aprendizaje",
        tipo_documento="reglamento",
        unidad_origen="Dirección Académica",
        numero_version="1",
        descripcion="Reglamento de Evaluación del Aprendizaje de la U.C.B.",
        observacion="Carga inicial de prueba",
        chunking_mode="normativo"
    )
    print(result)
finally:
    db.close()
