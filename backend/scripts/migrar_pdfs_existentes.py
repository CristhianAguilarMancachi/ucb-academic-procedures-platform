
"""
Importa PDF existentes a archivo_documento.

No crea documentos ni versiones nuevas.
No modifica los fragmentos ni embeddings RAG.

Ejecución dentro del contenedor backend:

Simulación:
    python scripts/migrar_pdfs_existentes.py

Importación:
    python scripts/migrar_pdfs_existentes.py --aplicar
"""

import argparse
import hashlib
import sys
from pathlib import Path

from sqlalchemy import select


# Permite ejecutar el script desde backend/scripts.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.core.config import DOCUMENTS_DIR  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

from app.models.archivo_documento import ArchivoDocumento  # noqa: E402
from app.models.version_documento import VersionDocumento  # noqa: E402
from app.models.documento_institucional import DocumentoInstitucional  # noqa: E402
from app.models.chunk_documento import ChunkDocumento  # noqa: E402


def hash_pdf(path: Path) -> str:
    sha = hashlib.sha256()

    with path.open("rb") as archivo:
        for bloque in iter(
            lambda: archivo.read(1024 * 1024),
            b"",
        ):
            sha.update(bloque)

    return sha.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Asociar PDF originales con "
            "versiones documentales existentes."
        ),
    )

    parser.add_argument(
        "--aplicar",
        action="store_true",
        help=(
            "Inserta los archivos en PostgreSQL. "
            "Sin esta opción solo verifica."
        ),
    )

    parser.add_argument(
        "--permitir-remoto",
        action="store_true",
        help=(
            "Permite utilizar una base de datos remota. "
            "Reservado para la migración posterior a Neon."
        ),
    )

    args = parser.parse_args()

    if not DOCUMENTS_DIR.is_dir():
        print(
            "ERROR: no se encontró el directorio "
            f"de documentos: {DOCUMENTS_DIR}"
        )
        return 1

    with SessionLocal() as db:
        host = db.get_bind().url.host or ""

        hosts_locales = {
            "postgres",
            "localhost",
            "127.0.0.1",
            "host.docker.internal",
        }

        if (
            host not in hosts_locales
            and not args.permitir_remoto
        ):
            print(
                "ERROR: se detectó una conexión "
                f"remota ({host})."
            )
            print(
                "No se modificó ningún registro. "
                "La migración a Neon se realizará "
                "por separado."
            )
            return 2

        modo = (
            "APLICAR"
            if args.aplicar
            else "SIMULACION"
        )

        print(
            f"Destino: host={host} | modo={modo}"
        )

        # ----------------------------------------------------
        # 1. Identificar los PDF existentes en el directorio.
        # ----------------------------------------------------

        rutas_por_hash: dict[str, list[Path]] = {}

        for path in sorted(
            DOCUMENTS_DIR.rglob("*.pdf")
        ):
            if (
                path.is_symlink()
                or not path.is_file()
            ):
                continue

            huella = hash_pdf(path)

            rutas_por_hash.setdefault(
                huella,
                [],
            ).append(path)

        print(
            "Archivos PDF localizados:",
            sum(
                len(rutas)
                for rutas in rutas_por_hash.values()
            ),
        )

        # ----------------------------------------------------
        # 2. Leer las versiones existentes en PostgreSQL.
        # ----------------------------------------------------

        versiones = db.scalars(
            select(VersionDocumento)
            .order_by(
                VersionDocumento.id_version_documento
            )
        ).all()

        existentes = set(
            db.scalars(
                select(
                    ArchivoDocumento.id_version_documento
                )
            ).all()
        )

        # ----------------------------------------------------
        # 3. Identificar los archivos pendientes.
        # ----------------------------------------------------

        insertar = []
        sin_archivo = 0

        for version in versiones:
            id_version = version.id_version_documento

            if id_version in existentes:
                print(
                    f"[YA ALMACENADO] Versión {id_version}"
                )
                continue

            hash_esperado = (
                version.hash_archivo or ""
            ).strip().lower()

            coincidencias = rutas_por_hash.get(
                hash_esperado,
                [],
            )

            if not coincidencias:
                sin_archivo += 1
                print(
                    f"[SIN PDF LOCAL] Versión {id_version}"
                    " - hash sin coincidencia"
                )
                continue

            # Coincidencia por SHA-256, sin rutas antiguas.
            path = coincidencias[0]

            print(
                f"[COINCIDE] Versión {id_version}"
                f" <- {path.name}"
                f" ({path.stat().st_size} bytes)"
            )

            insertar.append(
                (
                    id_version,
                    hash_esperado,
                    path,
                )
            )

        # ----------------------------------------------------
        # 4. Mostrar resumen.
        # ----------------------------------------------------

        print()
        print("===== RESUMEN =====")
        print(
            "Versiones registradas:",
            len(versiones),
        )
        print(
            "Versiones con PDF en PostgreSQL:",
            len(existentes),
        )
        print(
            "Archivos pendientes de importación:",
            len(insertar),
        )
        print(
            "Versiones sin archivo local:",
            sin_archivo,
        )

        if not args.aplicar:
            print()
            print(
                "Simulación terminada. "
                "No se modificó la base de datos."
            )
            return 0

        # ----------------------------------------------------
        # 5. Importar los binarios.
        # ----------------------------------------------------

        try:
            for (
                id_version,
                hash_esperado,
                path,
            ) in insertar:

                contenido = path.read_bytes()

                hash_real = hashlib.sha256(
                    contenido
                ).hexdigest()

                if hash_real != hash_esperado:
                    raise ValueError(
                        "El PDF de la versión "
                        f"{id_version} cambió durante "
                        "la importación."
                    )

                db.add(
                    ArchivoDocumento(
                        id_version_documento=id_version,
                        nombre_archivo_original=(
                            path.name[:255]
                        ),
                        contenido_pdf=contenido,
                    )
                )

            db.commit()

            print()
            print(
                "IMPORTACIÓN COMPLETADA:",
                len(insertar),
                "PDF almacenados en PostgreSQL.",
            )

            return 0

        except Exception as exc:
            db.rollback()

            print()
            print(
                "ERROR: la importación falló. "
                "Se revirtió la transacción."
            )
            print(str(exc))

            return 3


if __name__ == "__main__":
    raise SystemExit(main())
