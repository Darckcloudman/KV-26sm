# -*- coding: utf-8 -*-
"""
Менеджер подключений к базе данных.

Использует SQLAlchemy 2.0 с async support для PostgreSQL.
"""

import asyncio
import time
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError

from .config import Settings
from .logger import get_logger

logger = get_logger("DatabaseManager")


class DatabaseManager:
    """
    Менеджер подключений к PostgreSQL.
    
    Создаёт движок SQLAlchemy, управляет сессиями и пулом соединений.
    Для многопоточной работы (PyQt) используем asyncio.to_thread()
    для запуска async-кода в отдельном потоке.
    """
    
    def __init__(self, settings: Settings):
        """
        Инициализация менеджера подключений.
        
        Args:
            settings: Настройки приложения с параметрами БД.
        """
        self.settings = settings
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
    
    @property
    def engine(self) -> AsyncEngine:
        """Ленивая инициализация движка."""
        if self._engine is None:
            logger.info(
                "Инициализация движка SQLAlchemy: host=%s, db=%s, pool_size=%d",
                self.settings.db_host, self.settings.db_name, self.settings.db_pool_size
            )
            self._engine = create_async_engine(
                self.settings.database_url,
                pool_size=self.settings.db_pool_size,
                max_overflow=20,
                pool_pre_ping=True,  # Проверка соединения перед использованием
                echo=self.settings.db_echo,
                # Для PyQt: один поток = одно соединение из пула
                poolclass=NullPool if self.settings.db_pool_size == 1 else None,
            )
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Ленивая инициализация фабрики сессий."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Получить сессию для работы с БД.
        
        Usage:
            async with db_manager.get_session() as session:
                # работа с session
        """
        async with self.session_factory() as session:
            yield session
    
    async def init_db(self) -> None:
        """
        Создать все таблицы при первом запуске.
        
        Вызывается автоматически при старте с USE_DATABASE=true.
        """
        from .models.base import Base
        logger.info("Создание таблиц в БД...")
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы успешно созданы")
        except Exception as e:
            logger.error("Ошибка при создании таблиц: %s", e, exc_info=True)
            raise
    
    async def drop_db(self) -> None:
        """Удалить все таблицы (для отладки)."""
        from .models.base import Base
        logger.warning("Удаление всех таблиц БД!")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Таблицы удалены")
    
    async def close(self) -> None:
        """Закрыть все соединения и освободить ресурсы."""
        if self._engine is not None:
            logger.info("Закрытие соединений с БД")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    async def health_check(self) -> bool:
        """Проверить доступность базы данных."""
        try:
            async with self.session_factory() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            logger.debug("Health check БД: OK")
            return True
        except Exception as e:
            logger.warning("Health check БД не пройден: %s", e)
            return False

    async def connect_with_retry(self) -> bool:
        """
        Подключиться к БД с повторными попытками.
        
        Returns:
            True если подключение успешно, False после исчерпания попыток.
        """
        retries = self.settings.db_connect_retries
        delay = self.settings.db_connect_retry_delay
        
        for attempt in range(1, retries + 1):
            logger.info("Попытка подключения к PostgreSQL %d/%d", attempt, retries)
            try:
                # Проверяем соединение
                if await self.health_check():
                    logger.info("Подключение к PostgreSQL установлено")
                    return True
            except OperationalError as e:
                logger.error(
                    "Ошибка подключения (попытка %d/%d): %s",
                    attempt, retries, e
                )
                if attempt < retries:
                    logger.info("Повторная попытка через %.1f сек...", delay)
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(
                    "Неожиданная ошибка подключения (попытка %d/%d): %s",
                    attempt, retries, e, exc_info=True
                )
                if attempt < retries:
                    await asyncio.sleep(delay)
        
        logger.error("Не удалось подключиться к PostgreSQL после %d попыток", retries)
        return False
