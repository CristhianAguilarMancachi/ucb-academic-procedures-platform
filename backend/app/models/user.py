from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    contrasena_hash: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="activo")
    fecha_ultimo_acceso: Mapped[DateTime | None] = mapped_column(DateTime)
    fecha_creacion: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_actualizacion: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    rol = relationship("Role")