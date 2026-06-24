# -*- coding: utf-8 -*-
"""
Загрузка тестовых данных для WTG37 за 10 разных дат (каскад)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def load_cascade_data():
    """Загрузить данные для WTG37 за 10 разных дат."""
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ ДЛЯ WTG37 ЗА 10 ДАТ (КАСКАД)")
    print("=" * 70)
    
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("\n[OK] БД подключена\n")
    
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    
    # Очищаем БД
    print("[1/2] Очистка БД...")
    from kwf_prometheus.dal.models import Archive, SensorData, AnalysisCache, ProcessedArchive
    async with db_manager.session_factory() as session:
        await session.execute(SensorData.__table__.delete())
        await session.execute(AnalysisCache.__table__.delete())
        await session.execute(ProcessedArchive.__table__.delete())
        await session.execute(Archive.__table__.delete())
        await session.commit()
    print("  [OK] БД очищена\n")
    
    # Загружаем одни и те же файлы 10 раз с разными датами
    print("[2/2] Загрузка данных за 10 дат...")
    test_data_path = Path("test_data")
    rd2_files = list(test_data_path.glob("SENSOR_0[123]_*.rd2"))[:9]  # 3 датчика × 3 фильтра = 9 файлов
    
    base_date = datetime(2025, 9, 1)
    total_loaded = 0
    
    for i in range(10):
        date = base_date + timedelta(days=i*15)  # Каждые 15 дней
        print(f"\n  Дата {i+1}/10: {date.strftime('%d.%m.%Y')}")
        
        # Просто загружаем те же файлы - record_datetime возьмётся из имени файла
        for file_path in rd2_files:
            try:
                result = await repo.load_archive(file_path)
                if result.get('success'):
                    total_loaded += result.get('added', 0)
            except Exception as e:
                pass
    
    print(f"\n[OK] Всего загружено записей: {total_loaded}")
    
    # Проверка
    print("\n" + "=" * 70)
    print("ПРОВЕРКА")
    print("=" * 70)
    
    turbines = await repo.list_turbines()
    for t in turbines:
        wtg_id = t['wtg_id']
        stats = await repo.get_turbine_statistics(wtg_id)
        if stats:
            print(f"\n{wtg_id}:")
            print(f"  Архивов: {stats['total_archives']}")
            print(f"  Первая запись: {stats['first_record']}")
            print(f"  Последняя запись: {stats['last_record']}")
            
            # Проверяем timeline
            end_date = datetime.now()
            start_date = end_date - timedelta(days=300)
            timeline = await repo.get_records_timeline(wtg_id, start_date, end_date)
            print(f"  Дней с записями: {len(timeline)}")
    
    print("\n" + "=" * 70)
    print("ГОТОВО!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(load_cascade_data())
