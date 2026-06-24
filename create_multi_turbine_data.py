# -*- coding: utf-8 -*-
"""
Создание тестовых данных для нескольких турбин (имитация за разные даты)
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


async def create_multi_turbine_data():
    """Создать данные для 5 турбин за разные даты."""
    print("=" * 70)
    print("СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ НЕСКОЛЬКИХ ТУРБИН")
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
    
    # Копируем файлы test_data для разных турбин и дат
    print("[2/3] Копирование файлов для разных турбин...")
    test_data_path = Path("test_data")
    temp_path = Path("temp_test_data")
    temp_path.mkdir(exist_ok=True)
    
    # Генерируем файлы для 5 турбин за 5 разных дат
    turbines = ["WTG35", "WTG37", "WTG40", "WTG42", "WTG50"]
    base_date = datetime(2025, 9, 1)
    
    total_files = 0
    
    for i, wtg_id in enumerate(turbines):
        date = base_date + timedelta(days=i*30)  # Каждые 30 дней
        date_str = date.strftime("%Y%m%d")
        
        print(f"\n  {wtg_id} - {date.strftime('%d.%m.%Y')}")
        
        # Копируем 3 файла для датчика 1 (FILTER, LOW, HIGH)
        for sensor_id in [1, 2, 3]:
            for filter_type in ["FILTER", "LOW", "HIGH"]:
                src_file = list(test_data_path.glob(f"*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2"))[0]
                
                # Меняем имя файла для новой турбины и даты
                new_name = src_file.name.replace("WTG37", wtg_id).replace("20250901", date_str)
                dst_file = temp_path / new_name
                
                shutil.copy2(src_file, dst_file)
                total_files += 1
        
        print(f"    Создано файлов: {3*3}")
    
    print(f"\n[OK] Всего создано файлов: {total_files}\n")
    
    # Загружаем все файлы в БД
    print("[3/3] Загрузка в БД...")
    rd2_files = list(temp_path.glob("*.rd2"))
    
    added = 0
    skipped = 0
    errors = 0
    
    for i, file_path in enumerate(rd2_files, 1):
        if i % 10 == 0:
            print(f"  {i}/{len(rd2_files)}...")
        
        try:
            result = await repo.load_archive(file_path)
            
            if result.get('success'):
                added += result.get('added', 0)
                skipped += result.get('skipped', 0)
            else:
                errors += 1
                
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {file_path.name}: {e}")
    
    # Удаляем временную папку
    shutil.rmtree(temp_path)
    
    print(f"\n[OK] Загружено: {added}, Пропущено: {skipped}, Ошибок: {errors}\n")
    
    # Проверка
    print("=" * 70)
    print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
    print("=" * 70)
    
    turbines_in_db = await repo.list_turbines()
    print(f"\nТурбин в БД: {len(turbines_in_db)}")
    
    for t in turbines_in_db:
        wtg_id = t['wtg_id']
        stats = await repo.get_turbine_statistics(wtg_id)
        if stats:
            print(f"\n  {wtg_id}:")
            print(f"    Архивов: {stats.get('total_archives', 0)}")
            print(f"    Первая запись: {stats.get('first_record')}")
            print(f"    Последняя запись: {stats.get('last_record')}")
    
    print("\n" + "=" * 70)
    print("ГОТОВО!")
    print("=" * 70)
    print("\nТеперь в БД есть 5 турбин с данными за 5 месяцев.")
    print("Запустите приложение и проверьте вкладку 'Информация'.")


if __name__ == "__main__":
    asyncio.run(create_multi_turbine_data())
