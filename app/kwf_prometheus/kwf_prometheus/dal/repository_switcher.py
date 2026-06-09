# -*- coding: utf-8 -*-
"""
Механизм динамического переключения репозитория.

Позволяет переключаться между файловым режимом и PostgreSQL
без перезапуска приложения.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal

from .repositories.base import IVibrationRepository
from .repositories.postgres import PostgresRepository
from .repositories.file_system import FileSystemRepository
from .database import DatabaseManager
from .config import Settings
from .logger import get_logger

logger = get_logger("RepositorySwitcher")


class RepositorySwitcher(QObject):
    """
    Менеджер динамического переключения репозитория.
    
    Сигналы:
        repository_changed(repository): Эмитится при смене репозитория.
        connection_failed(error): Эмитится при ошибке подключения.
        connection_success(info): Эмитится при успешном подключении.
    """
    
    repository_changed = Signal(object)  # IVibrationRepository
    connection_failed = Signal(str)      # Сообщение об ошибке
    connection_success = Signal(str)     # Информация о подключении
    mode_changed = Signal(str)           # 'file' или 'postgres'
    
    def __init__(self, settings: Settings):
        """
        Инициализация переключателя.
        
        Args:
            settings: Текущие настройки приложения.
        """
        super().__init__()
        self.settings = settings
        self._repository: Optional[IVibrationRepository] = None
        self._db_manager: Optional[DatabaseManager] = None
        self._mode: str = 'file'  # 'file' или 'postgres'
    
    @property
    def repository(self) -> Optional[IVibrationRepository]:
        """Текущий репозиторий."""
        return self._repository
    
    @property
    def mode(self) -> str:
        """Текущий режим ('file' или 'postgres')."""
        return self._mode
    
    def initialize(self) -> IVibrationRepository:
        """
        Инициализировать репозиторий на основе текущих настроек.
        
        Returns:
            Репозиторий (файловый или PostgreSQL).
        """
        if self.settings.use_database:
            return self.switch_to_postgres()
        else:
            return self.switch_to_file()
    
    def switch_to_file(self) -> IVibrationRepository:
        """
        Переключиться на файловый репозиторий.
        
        Returns:
            FileSystemRepository.
        """
        logger.info("Переключение на файловый репозиторий")
        
        self._repository = FileSystemRepository(
            archive_storage_path=Path(self.settings.archive_storage_path)
        )
        self._mode = 'file'
        
        self.mode_changed.emit('file')
        self.repository_changed.emit(self._repository)
        self.connection_success.emit("Режим: Файловая система")
        
        return self._repository
    
    def switch_to_postgres(self) -> IVibrationRepository:
        """
        Переключиться на PostgreSQL репозиторий.
        
        Returns:
            PostgresRepository или FileSystemRepository при ошибке.
        """
        logger.info("Переключение на PostgreSQL репозиторий")
        
        try:
            # Создаём менеджер БД
            self._db_manager = DatabaseManager(self.settings)
            
            # Проверяем подключение
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                connected = loop.run_until_complete(
                    self._db_manager.connect_with_retry()
                )
                
                if not connected:
                    raise ConnectionError(
                        "Не удалось подключиться к PostgreSQL. "
                        "Проверьте параметры подключения."
                    )
                
                # Инициализируем БД (создание таблиц)
                loop.run_until_complete(self._db_manager.init_db())
                
            finally:
                loop.close()
            
            # Создаём репозиторий PostgreSQL
            self._repository = PostgresRepository(
                db_manager=self._db_manager,
                archive_storage_path=Path(self.settings.archive_storage_path)
            )
            self._mode = 'postgres'
            
            info = f"Режим: PostgreSQL ({self.settings.db_host}:{self.settings.db_port})"
            logger.info(info)
            
            self.mode_changed.emit('postgres')
            self.repository_changed.emit(self._repository)
            self.connection_success.emit(info)
            
            return self._repository
            
        except Exception as e:
            error_msg = f"Ошибка подключения к PostgreSQL: {e}"
            logger.error(error_msg, exc_info=True)
            
            self.connection_failed.emit(error_msg)
            
            # Fallback на файловый репозиторий
            logger.warning("Fallback на файловый репозиторий")
            return self.switch_to_file()
    
    def switch_mode(self, use_database: bool) -> IVibrationRepository:
        """
        Переключить режим хранения данных.
        
        Args:
            use_database: True для PostgreSQL, False для файлового режима.
            
        Returns:
            Новый репозиторий.
        """
        if use_database:
            return self.switch_to_postgres()
        else:
            return self.switch_to_file()
    
    def get_repository_info(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем репозитории.
        
        Returns:
            Словарь с информацией:
            - mode: 'file' или 'postgres'
            - host: Хост БД (для postgres)
            - path: Путь к хранилищу (для file)
            - connected: Статус подключения
        """
        info = {
            'mode': self._mode,
            'connected': self._repository is not None
        }
        
        if self._mode == 'postgres' and self._db_manager:
            info['host'] = self.settings.db_host
            info['port'] = self.settings.db_port
            info['database'] = self.settings.db_name
        else:
            info['path'] = str(self.settings.archive_storage_path)
        
        return info
