"""
Репозитории для доступа к данным.

Паттерн Repository - абстракция над источником данных.
Две реализации:
- FileSystemRepository - работа с файлами (режим v1.2)
- PostgresRepository - работа с PostgreSQL (режим v1.3)
"""

from .base import IVibrationRepository
from .file_system import FileSystemRepository
from .postgres import PostgresRepository
from .factory import get_repository

__all__ = [
    'IVibrationRepository',
    'FileSystemRepository',
    'PostgresRepository',
    'get_repository',
]
