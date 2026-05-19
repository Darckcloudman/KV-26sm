# -*- coding: utf-8 -*-
"""
Менеджер подключений к базе данных.

Использует SQLAlchemy 2.0 с async support для PostgreSQL.
"""

import asyncio
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool

from .config import Settings


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
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_db(self) -> None:
        """Удалить все таблицы (для отладки)."""
        from .models.base import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def close(self) -> None:
        """Закрыть все соединения и освободить ресурсы."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    async def health_check(self) -> bool:
        """Проверить доступность базы данных."""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False
