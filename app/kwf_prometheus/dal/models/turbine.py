# -*- coding: utf-8 -*-
"""
Модель турбины.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .sensor import Sensor
    from .archive import Archive


class Turbine(Base):
    """
    Модель турбины ВЭУ.
    
    Хранит основную информацию о ветротурбине и привязанный прибор SMP12C.
    Один прибор (по serial_number или MAC) закреплён за одной турбиной.
    """
    
    __tablename__ = "turbines"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    wtg_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        comment="Идентификатор турбины (например, WTG37)"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="Полное наименование турбины"
    )
    
    # === Идентификаторы прибора SMP12C ===
    device: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        comment="Модель устройства (например, 12C)"
    )
    serial_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="Серийный номер прибора (уникальный, главный идентификатор)"
    )
    mac_address: Mapped[str] = mapped_column(
        String(17),
        unique=True,
        nullable=True,
        index=True,
        comment="MAC-адрес прибора (уникальный, резервный идентификатор)"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=True,
        comment="IP-адрес прибора (может меняться)"
    )
    firmware_version: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        comment="Версия прошивки прибора"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата создания записи"
    )
    
    # Индексы для быстрого поиска
    __table_args__ = (
        Index('idx_turbine_wtg', 'wtg_id'),
        Index('idx_turbine_serial', 'serial_number'),
        Index('idx_turbine_mac', 'mac_address'),
    )
    
    # Отношения
    sensors: Mapped[list["Sensor"]] = relationship("Sensor", back_populates="turbine")
    archives: Mapped[list["Archive"]] = relationship("Archive", back_populates="turbine")
    
    def __repr__(self) -> str:
        return f"<Turbine(id={self.id}, wtg_id='{self.wtg_id}', serial='{self.serial_number}')>"
