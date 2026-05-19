"""
DAL (Data Access Layer) для SMP12C VibroDiag Analyzer v1.3

Слой доступа к данным с поддержкой:
- Файловая система (.zip/.rd2)
- PostgreSQL для хранения распарсенных данных
"""

from .config import settings
from .database import DatabaseManager

__all__ = ['settings', 'DatabaseManager']
__version__ = '1.3.0'
