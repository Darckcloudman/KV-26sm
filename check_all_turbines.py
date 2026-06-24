# -*- coding: utf-8 -*-
"""
Проверка всех турбин в БД
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def check_all_turbines():
    """Проверить все турбины в БД."""
    print("=" * 70)
    print("ПРОВЕРКА ВСЕХ ТУРБИН В БД")
    print("=" * 70)
    
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("\n[OK] БД подключена\n")
    
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    
    # Получаем список всех турбин
    turbines = await repo.list_turbines()
    
    if not turbines:
        print("[ERROR] В БД нет турбин!")
        print("\nНужно загрузить данные:")
        print("  1. Запустить приложение")
        print("  2. Home -> 'Загрузить архив'")
        print("  3. Выбрать файлы из test_data/")
        return
    
    print(f"Найдено турбин: {len(turbines)}\n")
    
    for t in turbines:
        wtg_id = t['wtg_id']
        print(f"{'='*70}")
        print(f"ВЭУ: {wtg_id}")
        print(f"{'='*70}")
        print(f"  Архивов: {t.get('total_archives', 0)}")
        
        # Статистика
        stats = await repo.get_turbine_statistics(wtg_id)
        if stats:
            print(f"  Первая запись: {stats.get('first_record')}")
            print(f"  Последняя запись: {stats.get('last_record')}")
            print(f"  Критических: {stats.get('critical_count', 0)}")
        
        # Проверяем датчики
        for sensor_id in [1, 2, 3, 5]:
            async with db_manager.session_factory() as session:
                from sqlalchemy import select, func
                from kwf_prometheus.dal.models import Archive, Turbine
                
                result = await session.execute(
                    select(Turbine).where(Turbine.wtg_id == wtg_id)
                )
                turbine = result.scalar_one_or_none()
                
                if turbine:
                    result = await session.execute(
                        select(func.count(Archive.id)).where(
                            Archive.turbine_id == turbine.id,
                            Archive.sensor_id == sensor_id,
                            Archive.filter_type == 'HIGH'
                        )
                    )
                    count = result.scalar()
                    if count > 0:
                        print(f"  Датчик {sensor_id} (HIGH): {count} архивов")
        
        print()
    
    print("=" * 70)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(check_all_turbines())
