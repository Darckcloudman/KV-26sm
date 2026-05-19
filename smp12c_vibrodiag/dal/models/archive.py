# -*- coding: utf-8 -*-
"""
Модель архивной записи.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Archive(Base):
    """
    Модель архивной записи (загруженный .zip или .rd2 файл).
    
    Хранит метаданные загруженного файла и ссылку на турбину.
    """
    
    __tablename__ = "archives"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    turbine_id: Mapped[int] = mapped_column(
        ForeignKey("turbines.id"),
        comment="Ссылка на турбину"
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=True,
        comment="Путь к исходному файлу"
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        comment="SHA256 хэш файла для дедупликации"
    )
    record_datetime: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="Дата-время записи из метаданных файла"
    )
    file_size_kb: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Размер файла в КБ"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата загрузки в БД"
    )
    
    # Отношения
    turbine: Mapped["Turbine"] = relationship("Turbine", back_populates="archives")
    sensor_data: Mapped[list["SensorData"]] = relationship(
        "SensorData",
        back_populates="archive",
        cascade="all, delete-orphan"
    )
    analysis_results: Mapped[list["AnalysisCache"]] = relationship(
        "AnalysisCache",
        back_populates="archive",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_archive_turbine_datetime', 'turbine_id', 'record_datetime'),
    )
    
    def __repr__(self) -> str:
        return f"<Archive(id={self.id}, turbine_id={self.turbine_id})>"
