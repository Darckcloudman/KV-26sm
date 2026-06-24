# -*- coding: utf-8 -*-
"""
РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РїСЂРёР»РѕР¶РµРЅРёСЏ KWF Prometheus v1.4.3

Р§РёС‚Р°РµС‚ РЅР°СЃС‚СЂРѕР№РєРё РёР· С„Р°Р№Р»Р° .env РІ РєРѕСЂРЅРµ РїСЂРѕРµРєС‚Р°.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """РќР°СЃС‚СЂРѕР№РєРё РїСЂРёР»РѕР¶РµРЅРёСЏ РёР· .env С„Р°Р№Р»Р°."""
    
    # Р’РµСЂСЃРёСЏ РїСЂРёР»РѕР¶РµРЅРёСЏ
    app_version: str = "1.4.3"
    
    # РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ Р±Р°Р·С‹ РґР°РЅРЅС‹С… (true/false)
    use_database: bool = False
    
    # РќР°СЃС‚СЂРѕР№РєРё PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "vibrodiag"
    db_user: str = "postgres"
    db_password: str = ""
    
    # Р Р°Р·РјРµСЂ РїСѓР»Р° СЃРѕРµРґРёРЅРµРЅРёР№
    db_pool_size: int = 10
    
    # Р›РѕРіРёСЂРѕРІР°РЅРёРµ SQL Р·Р°РїСЂРѕСЃРѕРІ
    db_echo: bool = False
    
    # РџРѕРІС‚РѕСЂРЅС‹Рµ РїРѕРїС‹С‚РєРё РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє Р‘Р”
    db_connect_retries: int = 3
    db_connect_retry_delay: float = 1.0
    
    # РЈСЂРѕРІРµРЅСЊ Р»РѕРіРёСЂРѕРІР°РЅРёСЏ DAL (DEBUG, INFO, WARNING, ERROR)
    log_level: str = "INFO"
    
    # РџСѓС‚СЊ Рє С…СЂР°РЅРёР»РёС‰Сѓ Р°СЂС…РёРІРѕРІ
    archive_storage_path: Path = Path("./test_data")
    
    # РђРІС‚РѕРїР°СЂСЃРёРЅРі С…СЂР°РЅРёР»РёС‰Р°
    auto_scan_enabled: bool = True
    auto_scan_interval_minutes: int = 10
    auto_scan_max_depth: int = 5
    
    @property
    def database_url(self) -> str:
        """РЎС‚СЂРѕРєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє PostgreSQL (async)."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """РЎС‚СЂРѕРєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє PostgreSQL (sync) РґР»СЏ Alembic."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        # РџРѕРґРґРµСЂР¶РєР° С‚РёРїР° Path
        json_encoders={Path: str}
    )


# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ РЅР°СЃС‚СЂРѕРµРє
settings = Settings()

