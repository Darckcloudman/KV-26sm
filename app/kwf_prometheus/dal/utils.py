# -*- coding: utf-8 -*-
"""
Утилиты для DAL.

Проверка подключения, очистка БД, и т.д.
"""

import asyncio
import sys
from pathlib import Path

from .config import settings


async def check_database_connection():
    """
    Проверить подключение к базе данных.
    
    Returns:
        True если подключение успешно, False иначе.
    """
    if not settings.use_database:
        print("PostgreSQL не включен (USE_DATABASE=false)")
        return False
    
    from .database import DatabaseManager
    
    db_manager = DatabaseManager(settings)
    
    try:
        connected = await db_manager.health_check()
        if connected:
            print(f"✓ Подключение к БД '{settings.db_name}' успешно")
        else:
            print(f"✗ Не удалось подключиться к БД")
        await db_manager.close()
        return connected
    except Exception as e:
        print(f"✗ Ошибка подключения: {e}")
        return False


async def drop_all_tables():
    """
    Удалить все таблицы из БД.
    
    ВНИМАНИЕ: Это удалит все данные!
    """
    if not settings.use_database:
        print("PostgreSQL не включен")
        return
    
    from .database import DatabaseManager
    from .models.base import Base
    
    db_manager = DatabaseManager(settings)
    
    try:
        await db_manager.drop_db()
        print("✓ Все таблицы удалены")
        await db_manager.close()
    except Exception as e:
        print(f"✗ Ошибка: {e}")


def main():
    """CLI для утилит DAL."""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python -m kwf_prometheus.dal.utils check  - проверка подключения")
        print("  python -m kwf_prometheus.dal.utils drop   - удалить все таблицы")
        return
    
    command = sys.argv[1]
    
    if command == "check":
        asyncio.run(check_database_connection())
    elif command == "drop":
        confirm = input("Вы уверены? Все данные будут удалены! (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(drop_all_tables())
        else:
            print("Отменено")
    else:
        print(f"Неизвестная команда: {command}")


if __name__ == "__main__":
    main()
