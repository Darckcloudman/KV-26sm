# -*- coding: utf-8 -*-
"""
Скрипт проверки подключения к БД и наличия данных.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def check_database():
    """Проверить БД и вывести статистику."""
    print("=" * 60)
    print("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БД")
    print("=" * 60)
    print(f"\nНастройки:")
    print(f"  Host: {settings.db_host}")
    print(f"  Port: {settings.db_port}")
    print(f"  Database: {settings.db_name}")
    print(f"  User: {settings.db_user}")
    print(f"  use_database: {settings.use_database}")
    
    db_manager = DatabaseManager(settings)
    
    print("\nПодключение к БД...")
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("[OK] Успешное подключение!")
    
    # Инициализируем БД
    print("\nИнициализация БД...")
    await db_manager.init_db()
    print("[OK] БД инициализирована")
    
    # Создаём репозиторий
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    
    # Получаем список турбин
    print("\nПолучение списка турбин...")
    turbines = await repo.list_turbines()
    
    if not turbines:
        print("[WARNING] В БД нет турбин")
    else:
        print(f"[OK] Найдено турбин: {len(turbines)}")
        for t in turbines[:10]:  # Первые 10
            print(f"  - {t['wtg_id']} (мощность: {t.get('power_kw', 'N/A')} кВт)")
    
    # Получаем статистику по первой турбине
    if turbines:
        wtg_id = turbines[0]['wtg_id']
        print(f"\nСтатистика для {wtg_id}:")
        stats = await repo.get_turbine_statistics(wtg_id)
        
        if stats:
            print(f"  Архивов: {stats.get('total_archives', 0)}")
            print(f"  Критических записей: {stats.get('critical_count', 0)}")
            print(f"  Первая запись: {stats.get('first_record')}")
            print(f"  Последняя запись: {stats.get('last_record')}")
        else:
            print("  [WARNING] Статистика не найдена")
    
    # Проверяем timeline
    if turbines:
        from datetime import datetime, timedelta
        wtg_id = turbines[0]['wtg_id']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        print(f"\nTimeline для {wtg_id} (120 дней):")
        timeline = await repo.get_records_timeline(wtg_id, start_date, end_date)
        
        if timeline:
            total_records = sum(timeline.values())
            print(f"  [OK] Дней с записями: {len(timeline)}")
            print(f"  [OK] Всего записей: {total_records}")
            # Последние 5 дней
            print("  Последние 5 дней:")
            for date, count in list(timeline.items())[-5:]:
                print(f"    {date}: {count} записей")
        else:
            print("  [WARNING] Timeline пуст")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_database())
