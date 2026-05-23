# -*- coding: utf-8 -*-
"""
Фабрика репозиториев.

Создаёт нужную реализацию репозитория на основе настроек.
При ошибке подключения к PostgreSQL автоматически переключается на FileSystemRepository.
"""

from pathlib import Path
from typing import Union

from ..config import Settings
from ..database import DatabaseManager
from ..logger import get_logger
from .base import IVibrationRepository
from .file_system import FileSystemRepository
from .postgres import PostgresRepository

logger = get_logger("RepositoryFactory")


def get_repository(settings: Settings) -> IVibrationRepository:
    """
    Создать репозиторий на основе настроек.
    
    При включённом USE_DATABASE пытается подключиться к PostgreSQL.
    Если подключение не удалось — возвращается FileSystemRepository.
    
    Args:
        settings: Настройки приложения.
        
    Returns:
        Реализация IVibrationRepository.
    """
    if settings.use_database:
        logger.info("Режим PostgreSQL включен, попытка подключения...")
        db_manager = DatabaseManager(settings)
        
        # Проверяем подключение с повторными попытками
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                connected = loop.run_until_complete(db_manager.connect_with_retry())
            else:
                # Event loop уже запущен (например, в PyQt)
                connected = loop.run_until_complete(db_manager.connect_with_retry())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            connected = loop.run_until_complete(db_manager.connect_with_retry())
        
        if connected:
            # Инициализация БД (создание таблиц)
            try:
                asyncio.run(db_manager.init_db())
            except RuntimeError:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(db_manager.init_db())
            
            logger.info("PostgreSQL подключен, создаём PostgresRepository")
            return PostgresRepository(
                db_manager=db_manager,
                archive_storage_path=settings.archive_storage_path
            )
        else:
            # Fallback на файловую систему
            logger.warning(
                "Не удалось подключиться к PostgreSQL. "
                "Переключение на FileSystemRepository. "
                "Проверьте настройки подключения (DB_HOST, DB_USER, DB_PASSWORD)."
            )
            return FileSystemRepository(
                archive_storage_path=settings.archive_storage_path
            )
    else:
        # Режим файловой системы (по умолчанию)
        logger.info("Режим файловой системы")
        return FileSystemRepository(
            archive_storage_path=settings.archive_storage_path
        )
