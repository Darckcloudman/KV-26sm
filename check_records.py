# -*- coding: utf-8 -*-
"""
Проверка количества записей в БД.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository
from sqlalchemy import select, func


async def check_records():
    """Проверить количество записей."""
    print("=" * 60)
    print("ПРОВЕРКА ЗАПИСЕЙ В БД")
    print("=" * 60)
    
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться")
        return
    
    async with db_manager.session_factory() as session:
        from kwf_prometheus.dal.models import Archive, SensorData, AnalysisCache
        
        # Количество архивов
        result = await session.execute(select(func.count(Archive.id)))
        archive_count = result.scalar()
        print(f"\nАрхивов: {archive_count}")
        
        # Количество записей sensor_data
        result = await session.execute(select(func.count(SensorData.id)))
        sensor_data_count = result.scalar()
        print(f"Записей sensor_data: {sensor_data_count}")
        
        # Количество записей analysis_cache
        result = await session.execute(select(func.count(AnalysisCache.id)))
        analysis_count = result.scalar()
        print(f"Записей analysis_cache: {analysis_count}")
        
        # Архивы по датчикам
        print("\nАрхивы по датчикам:")
        result = await session.execute(
            select(Archive.sensor_id, func.count(Archive.id))
            .group_by(Archive.sensor_id)
            .order_by(Archive.sensor_id)
        )
        for sensor_id, count in result.all():
            print(f"  Датчик {sensor_id}: {count} архивов")
        
        # Архивы по фильтрам
        print("\nАрхивы по фильтрам:")
        result = await session.execute(
            select(Archive.filter_type, func.count(Archive.id))
            .group_by(Archive.filter_type)
            .order_by(Archive.filter_type)
        )
        for filter_type, count in result.all():
            print(f"  {filter_type}: {count} архивов")
        
        # Проверка file_hash
        print("\nПроверка file_hash:")
        result = await session.execute(
            select(Archive.file_path, Archive.file_hash)
            .where(Archive.file_hash == '')
            .limit(5)
        )
        empty_hash = result.all()
        if empty_hash:
            print(f"  [WARNING] Найдено {len(empty_hash)} архивов с пустым hash")
            for path, hash in empty_hash:
                print(f"    - {path}")
        else:
            print("  [OK] Все архивы имеют hash")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_records())
