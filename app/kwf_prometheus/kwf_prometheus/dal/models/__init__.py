"""
Модели SQLAlchemy для PostgreSQL.

Содержит сущности для хранения:
- Турбин
- Архивных записей
- Датчиков (с привязкой к компонентам)
- Данных датчиков
- Результатов анализа
"""

from .base import Base
from .turbine import Turbine
from .archive import Archive
from .sensor import Sensor, ComponentType
from .sensor_data import SensorData
from .analysis_cache import AnalysisCache
from .processed_archive import ProcessedArchive

__all__ = [
    'Base',
    'Turbine',
    'Archive',
    'Sensor',
    'ComponentType',
    'SensorData',
    'AnalysisCache',
    'ProcessedArchive',
]
