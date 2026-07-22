from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Role(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    fecha_actualizacion: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())