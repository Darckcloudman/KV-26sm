# -*- coding: utf-8 -*-
"""
Модель данных датчика.

Хранит временные ряды для каждого датчика и типа фильтра.
"""

from datetime import datetime
from sqlalchemy import (
    Integer, Float, String, DateTime, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SensorData(Base):
    """
    Модель данных датчика.
    
    Хранит временные ряды (timestamps + values) для каждого
    датчика (1-8) и типа фильтра (FILTER/LOW/HIGH).
    
    Использует PostgreSQL ARRAY для хранения массивов double precision.
    """
    
    __tablename__ = "sensor_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    archive_id: Mapped[int] = mapped_column(
        ForeignKey("archives.id", ondelete="CASCADE"),
        comment="Ссылка на архивную запись"
    )
    sensor_id: Mapped[int] = mapped_column(
        Integer,
        comment="Номер датчика (1-8)"
    )
    filter_type: Mapped[str] = mapped_column(
        String(20),
        comment="Тип фильтра: FILTER (0.1-10 Гц), LOW (10-1000 Гц), HIGH (0-12 кГц)"
    )
    
    # Временные ряды
    timestamps: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=True,
        comment="Временные метки (секунды)"
    )
    values: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=True,
        comment="Значения виброскорости (мм/с)"
    )
    
    # Метаданные
    sampling_frequency: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Частота дискретизации (Гц)"
    )
    samples_count: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        comment="Количество отсчётов"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата сохранения в БД"
    )
    
    # Отношения
    archive: Mapped["Archive"] = relationship("Archive", back_populates="sensor_data")
    
    # Уникальный индекс для предотвращения дубликатов
    __table_args__ = (
        UniqueConstraint('archive_id', 'sensor_id', 'filter_type', 
                         name='uix_sensor_data'),
        Index('idx_sensor_data_archive', 'archive_id'),
        Index('idx_sensor_data_sensor', 'sensor_id', 'filter_type'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<SensorData(id={self.id}, sensor_id={self.sensor_id}, "
            f"filter_type='{self.filter_type}', archive_id={self.archive_id})>"
        )
