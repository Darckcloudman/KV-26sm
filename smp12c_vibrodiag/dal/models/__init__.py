"""
Модели SQLAlchemy для PostgreSQL.

Содержит сущности для хранения:
- Турбин
- Архивных записей
- Данных датчиков
- Результатов анализа
"""

from .base import Base
from .turbine import Turbine
from .archive import Archive
from .sensor_data import SensorData
from .analysis_cache import AnalysisCache

__all__ = ['Base', 'Turbine', 'Archive', 'SensorData', 'AnalysisCache']
