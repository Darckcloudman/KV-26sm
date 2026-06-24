# -*- coding: utf-8 -*-
"""
Скрипт создания базы данных vibrodiag.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager


async def create_database():
    """Создать БД vibrodiag если не существует."""
    print("=" * 60)
    print("СОЗДАНИЕ БАЗЫ ДАННЫХ")
    print("=" * 60)
    print(f"\nНастройки:")
    print(f"  Host: {settings.db_host}")
    print(f"  Port: {settings.db_port}")
    print(f"  Database: {settings.db_name}")
    print(f"  User: {settings.db_user}")
    
    # Создаём менеджер БД
    db_manager = DatabaseManager(settings)
    
    print("\nПопытка подключения...")
    connected = await db_manager.connect_with_retry()
    
    if connected:
        print("[OK] Подключение успешно!")
        
        # Инициализируем БД (создаёт таблицы)
        print("\nИнициализация БД (создание таблиц)...")
        await db_manager.init_db()
        print("[OK] Таблицы созданы!")
        
        # Проверяем таблицы
        async with db_manager.session_factory() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
            )
            tables = [row[0] for row in result.all()]
            
            print(f"\n[OK] Создано таблиц: {len(tables)}")
            for table in tables:
                print(f"  - {table}")
    else:
        print("[ERROR] Не удалось подключиться к БД")
        print("\nВозможные причины:")
        print("  1. PostgreSQL не запущен")
        print("  2. Неверные учётные данные в .env")
        print("  3. База данных не существует")
        print("\nПопробуйте создать БД вручную:")
        print(f"  CREATE DATABASE {settings.db_name};")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(create_database())
