# -*- coding: utf-8 -*-
"""
Модель турбины.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Turbine(Base):
    """
    Модель турбины ВЭУ.
    
    Хранит основную информацию о ветротурбине.
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата создания записи"
    )
    
    def __repr__(self) -> str:
        return f"<Turbine(id={self.id}, wtg_id='{self.wtg_id}')>"
