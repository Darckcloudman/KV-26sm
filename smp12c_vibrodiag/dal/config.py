# -*- coding: utf-8 -*-
"""
Конфигурация приложения SMP12C VibroDiag Analyzer v1.3

Читает настройки из файла .env в корне проекта.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из .env файла."""
    
    # Версия приложения
    app_version: str = "1.3"
    
    # Использование базы данных (true/false)
    use_database: bool = False
    
    # Настройки PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "vibrodiag"
    db_user: str = "postgres"
    db_password: str = ""
    
    # Размер пула соединений
    db_pool_size: int = 10
    
    # Логирование SQL запросов
    db_echo: bool = False
    
    # Путь к хранилищу архивов
    archive_storage_path: Path = Path("./test_data")
    
    @property
    def database_url(self) -> str:
        """Строка подключения к PostgreSQL (async)."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """Строка подключения к PostgreSQL (sync) для Alembic."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Поддержка типа Path
        json_encoders = {Path: str}


# Глобальный экземпляр настроек
settings = Settings()
