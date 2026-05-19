# -*- coding: utf-8 -*-
"""
Фабрика репозиториев.

Создаёт нужную реализацию репозитория на основе настроек.
"""

from pathlib import Path
from typing import Union

from ..config import Settings
from ..database import DatabaseManager
from .base import IVibrationRepository
from .file_system import FileSystemRepository
from .postgres import PostgresRepository


def get_repository(settings: Settings) -> IVibrationRepository:
    """
    Создать репозиторий на основе настроек.
    
    Args:
        settings: Настройки приложения.
        
    Returns:
        Реализация IVibrationRepository.
    """
    if settings.use_database:
        # Режим PostgreSQL
        db_manager = DatabaseManager(settings)
        
        # Инициализация БД (создание таблиц)
        import asyncio
        try:
            asyncio.run(db_manager.init_db())
        except RuntimeError:
            # Если event loop уже запущен (например, в PyQt)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(db_manager.init_db())
        
        return PostgresRepository(
            db_manager=db_manager,
            archive_storage_path=settings.archive_storage_path
        )
    else:
        # Режим файловой системы (по умолчанию)
        return FileSystemRepository(
            archive_storage_path=settings.archive_storage_path
        )
