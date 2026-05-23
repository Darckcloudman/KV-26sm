# -*- coding: utf-8 -*-
"""
Модель кэша результатов анализа.

Хранит предвычисленные результаты для быстрого доступа:
- RMS, зона состояния, пики спектра
- Спектр (частоты, амплитуды)
"""

from datetime import datetime
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AnalysisCache(Base):
    """
    Кэш результатов анализа.
    
    При первом анализе данные вычисляются и сохраняются сюда.
    При повторном открытии архива берутся из БД без пересчёта.
    """
    
    __tablename__ = "analysis_cache"
    
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
        comment="Тип фильтра: FILTER/LOW/HIGH"
    )
    
    # Результаты анализа
    rms_total: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Общее СКЗ для всего сигнала (мм/с)"
    )
    zone: Mapped[str] = mapped_column(
        String(1),
        nullable=True,
        comment="Зона состояния по ISO 10816: A/B/C/D"
    )
    peak: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Пиковое значение"
    )
    peak_to_peak: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Размах сигнала"
    )
    
    # Спектр
    spectrum_frequencies: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=True,
        comment="Частоты спектра (Гц)"
    )
    spectrum_amplitudes: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=True,
        comment="Амплитуды спектра"
    )
    
    # Пики в спектре
    peaks: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        comment="Топ-N пиков: [{frequency, amplitude}, ...]"
    )
    
    # Метаданные
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата и время анализа"
    )
    
    # Отношения
    archive: Mapped["Archive"] = relationship("Archive", back_populates="analysis_results")
    
    # Уникальный индекс
    __table_args__ = (
        UniqueConstraint('archive_id', 'sensor_id', 'filter_type',
                         name='uix_analysis_cache'),
        Index('idx_analysis_archive', 'archive_id'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AnalysisCache(id={self.id}, sensor_id={self.sensor_id}, "
            f"zone='{self.zone}', rms={self.rms_total:.3f})>"
        )
