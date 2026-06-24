# -*- coding: utf-8 -*-
"""
Очистка БД для повторной загрузки данных.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from sqlalchemy import text


async def clear_db():
    """Очистить все таблицы."""
    print("=" * 60)
    print("ОЧИСТКА БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться")
        return
    
    print("\nПодключение успешно!")
    print("Удаление всех данных из таблиц...")
    
    async with db_manager.session_factory() as session:
        # Отключаем foreign key checks
        await session.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        
        # Очищаем таблицы в правильном порядке (из-за FK)
        tables = [
            'analysis_cache',
            'sensor_data', 
            'processed_archives',
            'archives',
            'sensors',
            'turbines'
        ]
        
        for table in tables:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"  [OK] Очищена таблица: {table}")
        
        await session.commit()
    
    print("\n" + "=" * 60)
    print("БД очищена!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(clear_db())
