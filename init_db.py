# -*- coding: utf-8 -*-
"""
Скрипт инициализации БД - создание таблиц через Alembic.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def init_db():
    """Инициализировать БД - создать таблицы."""
    print("=" * 60)
    print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    db_manager = DatabaseManager(settings)
    
    print("\nПодключение к БД...")
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("[OK] Подключение успешно!")
    
    # Инициализируем БД (создаёт таблицы через SQLAlchemy)
    print("\nСоздание таблиц...")
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
    
    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
