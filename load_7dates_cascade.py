# -*- coding: utf-8 -*-
"""
Загрузка данных для WTG37 за 7 разных дат для каскада спектров
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def load_7dates_data():
    """Загрузить данные для WTG37 за 7 разных дат."""
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ ДЛЯ WTG37 ЗА 7 ДАТ (КАСКАД)")
    print("=" * 70)
    
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("\n[OK] БД подключена\n")
    
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    
    # Очищаем БД
    print("[1/3] Очистка БД...")
    from kwf_prometheus.dal.models import Archive, SensorData, AnalysisCache, ProcessedArchive
    async with db_manager.session_factory() as session:
        await session.execute(SensorData.__table__.delete())
        await session.execute(AnalysisCache.__table__.delete())
        await session.execute(ProcessedArchive.__table__.delete())
        await session.execute(Archive.__table__.delete())
        await session.commit()
    print("  [OK] БД очищена\n")
    
    # Копируем файлы для 7 дат
    print("[2/3] Копирование файлов для 7 дат...")
    test_data_path = Path("test_data")
    temp_path = Path("temp_cascade_data")
    temp_path.mkdir(exist_ok=True)
    
    # 7 дат с интервалом 30 дней
    dates = [
        datetime(2025, 7, 1),
        datetime(2025, 8, 1),
        datetime(2025, 9, 1),
        datetime(2025, 10, 1),
        datetime(2025, 11, 1),
        datetime(2025, 12, 1),
        datetime(2026, 1, 1),
    ]
    
    # Копируем 3 файла для датчика 2 (FILTER, LOW, HIGH) для каждой даты
    files_to_copy = []
    for sensor_id in [2]:  # Датчик 2 (как на белом скриншоте)
        for filter_type in ["FILTER", "LOW", "HIGH"]:
            src_file = list(test_data_path.glob(f"*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2"))[0]
            
            for i, date in enumerate(dates):
                date_str = date.strftime("%Y%m%d")
                new_name = src_file.name.replace("20250901", date_str)
                dst_file = temp_path / new_name
                shutil.copy2(src_file, dst_file)
                files_to_copy.append(dst_file)
    
    print(f"  Создано файлов: {len(files_to_copy)}")
    print(f"  Дат: {len(dates)}")
    print(f"  Файлов на дату: {len(files_to_copy) // len(dates)}\n")
    
    # Загружаем все файлы в БД
    print("[3/3] Загрузка в БД...")
    total_added = 0
    total_skipped = 0
    total_errors = 0
    
    for i, file_path in enumerate(files_to_copy, 1):
        try:
            result = await repo.load_archive(file_path)
            
            if result.get('success'):
                added = result.get('added', 0)
                skipped = result.get('skipped', 0)
                total_added += added
                total_skipped += skipped
                
                if i % 3 == 0:
                    print(f"  {i}/{len(files_to_copy)}: {file_path.name[:50]}... (+{added})")
            else:
                total_errors += 1
                print(f"  [ERROR] {file_path.name}")
                
        except Exception as e:
            total_errors += 1
            print(f"  [ERROR] {file_path.name}: {e}")
    
    # Удаляем временную папку
    shutil.rmtree(temp_path)
    
    print(f"\n[OK] Загружено: {total_added}, Пропущено: {total_skipped}, Ошибок: {total_errors}\n")
    
    # Проверка
    print("=" * 70)
    print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
    print("=" * 70)
    
    turbines = await repo.list_turbines()
    for t in turbines:
        wtg_id = t['wtg_id']
        print(f"\n{wtg_id}:")
        
        stats = await repo.get_turbine_statistics(wtg_id)
        if stats:
            print(f"  Архивов: {stats['total_archives']}")
            print(f"  Первая запись: {stats['first_record']}")
            print(f"  Последняя запись: {stats['last_record']}")
        
        # Проверяем timeline
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)
        timeline = await repo.get_records_timeline(wtg_id, start_date, end_date)
        print(f"  Дней с записями: {len(timeline)}")
        
        # Проверяем датчик 2
        async with db_manager.session_factory() as session:
            from sqlalchemy import select, func
            from kwf_prometheus.dal.models import Archive, Turbine
            
            result = await session.execute(select(Turbine).where(Turbine.wtg_id == wtg_id))
            turbine = result.scalar_one_or_none()
            
            if turbine:
                for filter_type in ["FILTER", "LOW", "HIGH"]:
                    result = await session.execute(
                        select(func.count(Archive.id)).where(
                            Archive.turbine_id == turbine.id,
                            Archive.sensor_id == 2,
                            Archive.filter_type == filter_type
                        )
                    )
                    count = result.scalar()
                    print(f"  Датчик 2 ({filter_type}): {count} архивов")
    
    print("\n" + "=" * 70)
    print("ГОТОВО!")
    print("=" * 70)
    print("\nТеперь в БД есть WTG37 с данными за 7 дат.")
    print("Запустите приложение, загрузите любой файл WTG37 и проверьте каскад.")


if __name__ == "__main__":
    asyncio.run(load_7dates_data())
