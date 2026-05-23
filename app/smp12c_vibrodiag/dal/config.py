# -*- coding: utf-8 -*-
"""
Конфигурация приложения KWF Prometheus v1.4.1

Читает настройки из файла .env в корне проекта.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    # Повторные попытки подключения к БД
    db_connect_retries: int = 3
    db_connect_retry_delay: float = 1.0
    
    # Уровень логирования DAL (DEBUG, INFO, WARNING, ERROR)
    log_level: str = "INFO"
    
    # Путь к хранилищу архивов
    archive_storage_path: Path = Path("./test_data")
    
    # Автопарсинг хранилища
    auto_scan_enabled: bool = True
    auto_scan_interval_minutes: int = 10
    auto_scan_max_depth: int = 5
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        # Поддержка типа Path
        json_encoders={Path: str}
    )


# Глобальный экземпляр настроек
settings = Settings()
