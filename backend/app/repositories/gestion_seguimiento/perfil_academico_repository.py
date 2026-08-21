from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gestion_seguimiento.perfil_academico import (
    PerfilAcademico,
)


def obtener_perfil_por_usuario(
    db: Session,
    id_usuario: int,
) -> PerfilAcademico | None:
    stmt = (
        select(PerfilAcademico)
        .where(
            PerfilAcademico.id_usuario == id_usuario
        )
    )

    return db.scalar(stmt)


def crear_perfil(
    db: Session,
    *,
    id_usuario: int,
    codigo_estudiante: str | None = None,
    sede: str | None = None,
    carrera_programa: str | None = None,
    nivel_academico: str | None = None,
    documento_identidad: str | None = None,
) -> PerfilAcademico:
    perfil = PerfilAcademico(
        id_usuario=id_usuario,
        codigo_estudiante=codigo_estudiante,
        sede=sede,
        carrera_programa=carrera_programa,
        nivel_academico=nivel_academico,
        documento_identidad=documento_identidad,
    )

    db.add(perfil)
    db.flush()
    db.refresh(perfil)

    return perfil


def actualizar_perfil(
    db: Session,
    perfil: PerfilAcademico,
    *,
    cambios: dict[str, Any],
) -> PerfilAcademico:
    campos_permitidos = {
        "codigo_estudiante",
        "sede",
        "carrera_programa",
        "nivel_academico",
        "documento_identidad",
    }

    for campo, valor in cambios.items():
        if campo in campos_permitidos:
            setattr(perfil, campo, valor)

    db.flush()
    db.refresh(perfil)

    return perfil