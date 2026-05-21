# -*- coding: utf-8 -*-
"""
Модель архивной записи.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Index
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
    # Метрики турбины из метаданных файла
    power_kw: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Активная мощность (кВт)"
    )
    generator_speed_rpm: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Частота вращения генератора (RPM)"
    )
    wind_speed_ms: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Скорость ветра (м/с)"
    )
    cumulative_power_kwh: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Накопленная выработка (кВт·ч)"
    )
    
    # === Идентификаторы записи (для дедупликации) ===
    sensor_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Номер датчика (1-8)"
    )
    filter_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Тип фильтра: FILTER, LOW, HIGH"
    )
    sensor_serial: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Порядковый номер записи за сутки (record_number). Все .rd2 файлы одного архива имеют одинаковое значение. Информационное поле, НЕ используется для дедупликации."
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
        Index('idx_archive_sensor', 'sensor_id', 'filter_type'),
        # Уникальный ключ для дедупликации записей
        Index('uq_archive_unique_record', 'turbine_id', 'record_datetime', 'sensor_id', 'filter_type', unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Archive(id={self.id}, turbine_id={self.turbine_id})>"
