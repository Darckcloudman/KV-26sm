"""
DAL (Data Access Layer) для KWF Prometheus v1.4.1

Слой доступа к данным с поддержкой:
"""

from .config import settings
from .database import DatabaseManager

__all__ = ['settings', 'DatabaseManager']
__version__ = '1.3.0'
