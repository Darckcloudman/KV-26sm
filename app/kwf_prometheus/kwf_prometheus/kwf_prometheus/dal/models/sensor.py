# -*- coding: utf-8 -*-
"""
Модель датчиков и их привязка к компонентам турбины.

Датчики 1-5: Редуктор (Gearbox)
Датчики 6-8: Генератор (Generator)
"""

from datetime import datetime
from enum import Enum
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, Enum as SQLEnum, Index, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .turbine import Turbine


class ComponentType(Enum):
    """Тип компонента турбины."""
    GEARBOX = 'gearbox'      # Редуктор (датчики 1-5)
    GENERATOR = 'generator'  # Генератор (датчики 6-8)
    OTHER = 'other'          # Другое


class Sensor(Base):
    """
    Модель датчика с привязкой к компоненту.
    
    Датчики 1-5: Редуктор (Gearbox)
    Датчики 6-8: Генератор (Generator)
    """
    
    __tablename__ = "sensors"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    turbine_id: Mapped[int] = mapped_column(
        ForeignKey("turbines.id"),
        comment="Ссылка на турбину"
    )
    position_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Позиция датчика (1-8)",
        index=True
    )
    description: Mapped[str] = mapped_column(
        String(200),
        nullable=True,
        comment="Описание позиции датчика"
    )
    
    # === Тип компонента ===
    component_type: Mapped[ComponentType] = mapped_column(
        SQLEnum(ComponentType),
        nullable=False,
        comment="Тип компонента: gearbox (1-5), generator (6-8)",
        index=True
    )
    
    # === Настройки датчика ===
    sensor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="Тип датчика: acceleration, velocity"
    )
    frequency_range_low: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Нижняя граница частотного диапазона (Гц)"
    )
    frequency_range_high: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="Верхняя граница частотного диапазона (Гц)"
    )
    
    # === Метки для анализа ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Активен ли датчик"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата создания записи"
    )
    
    # Отношения
    turbine: Mapped["Turbine"] = relationship("Turbine", back_populates="sensors")
    
    # Индексы
    __table_args__ = (
        Index('idx_sensor_turbine_position', 'turbine_id', 'position_code', unique=True),
        Index('idx_sensor_component', 'component_type', 'position_code'),
    )
    
    def __repr__(self) -> str:
        return f"<Sensor(position={self.position_code}, type={self.component_type.value})>"
    
    @staticmethod
    def get_component_type_for_position(position: int) -> ComponentType:
        """
        Получить тип компонента для позиции датчика.
        
        Args:
            position: Номер позиции (1-8)
        
        Returns:
            ComponentType: GEARBOX для 1-5, GENERATOR для 6-8
        """
        if 1 <= position <= 5:
            return ComponentType.GEARBOX
        elif 6 <= position <= 8:
            return ComponentType.GENERATOR
        else:
            return ComponentType.OTHER
    
    @staticmethod
    def get_gearbox_sensors() -> List[int]:
        """Получить список позиций датчиков редуктора."""
        return [1, 2, 3, 4, 5]
    
    @staticmethod
    def get_generator_sensors() -> List[int]:
        """Получить список позиций датчиков генератора."""
        return [6, 7, 8]
