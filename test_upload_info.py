# -*- coding: utf-8 -*-
"""
Тест проверки работы вкладки "Информация о загрузке"
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def test_upload_info_screen():
    """Протестировать данные для вкладки "Информация"."""
    print("=" * 70)
    print("ТЕСТ: Вкладка 'Информация о загрузке'")
    print("=" * 70)
    
    # 1. Проверка подключения к БД
    print("\n[1/5] Проверка подключения к БД...")
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("  [ERROR] Не удалось подключиться к БД")
        print(f"  Проверьте .env файл:")
        print(f"    use_database={settings.use_database}")
        print(f"    db_host={settings.db_host}")
        print(f"    db_name={settings.db_name}")
        return
    
    print("  [OK] БД подключена")
    
    # 2. Проверка наличия турбин
    print("\n[2/5] Проверка турбин в БД...")
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    turbines = await repo.list_turbines()
    
    if not turbines:
        print("  [ERROR] В БД нет турбин")
        print("  Нужно загрузить данные через GUI или скрипт")
    else:
        print(f"  [OK] Найдено турбин: {len(turbines)}")
        for t in turbines:
            print(f"    - {t['wtg_id']} (архивов: {t.get('total_archives', 0)})")
    
    # 3. Проверка статистики по WTG40 (с скриншота)
    if turbines:
        wtg_id = turbines[0]['wtg_id']
        print(f"\n[3/5] Проверка статистики для {wtg_id}...")
        stats = await repo.get_turbine_statistics(wtg_id)
        
        if stats:
            print(f"  [OK] Статистика:")
            print(f"    Архивов: {stats.get('total_archives', 0)}")
            print(f"    Первая запись: {stats.get('first_record')}")
            print(f"    Последняя запись: {stats.get('last_record')}")
            print(f"    Критических: {stats.get('critical_count', 0)}")
        else:
            print(f"  [ERROR] Статистика не найдена")
    
    # 4. Проверка timeline (для правого графика)
    if turbines:
        wtg_id = turbines[0]['wtg_id']
        print(f"\n[4/5] Проверка timeline для {wtg_id}...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        timeline = await repo.get_records_timeline(wtg_id, start_date, end_date)
        
        if timeline and len(timeline) > 0:
            total = sum(timeline.values())
            print(f"  [OK] Timeline:")
            print(f"    Дней с записями: {len(timeline)}")
            print(f"    Всего записей: {total}")
            print(f"    Последние 3 дня:")
            for date, count in list(timeline.items())[-3:]:
                print(f"      {date}: {count}")
        else:
            print(f"  [ERROR] Timeline пуст")
            print(f"     График 'Количество записей' не отобразится")
    
    # 5. Проверка спектра ВЧ(ф) (для левого графика)
    if turbines:
        wtg_id = turbines[0]['wtg_id']
        sensor_id = 3  # Датчик 3 как на скриншоте
        print(f"\n[5/5] Проверка спектра ВЧ(ф) для {wtg_id}, датчик {sensor_id}...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        spectrum_data = await repo.get_vh_spectrum_data(wtg_id, sensor_id, start_date, end_date)
        
        if spectrum_data and len(spectrum_data) > 0:
            print(f"  [OK] Спектр ВЧ(ф):")
            print(f"    Точек данных: {len(spectrum_data)}")
            print(f"    Пример первой точки:")
            point = spectrum_data[0]
            print(f"      Дата: {point.get('timestamp')}")
            print(f"      Частота: {point.get('frequency', 0):.2f} Гц")
            print(f"      Амплитуда: {point.get('amplitude', 0):.4f} мм/с²")
        else:
            print(f"  [ERROR] Спектр ВЧ(ф) пуст")
            print(f"     График 'ВЧ(ф) СПЕКТР (3D)' не отобразится")
            
            # Проверим, есть ли вообще архивы для датчика 3
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
                            Archive.filter_type == 'HIGH'  # ВЧ спектр
                        )
                    )
                    count = result.scalar()
                    print(f"    Архивов для датчика {sensor_id} (HIGH): {count}")
    
    # ИТОГИ
    print("\n" + "=" * 70)
    print("ИТОГИ ТЕСТА")
    print("=" * 70)
    
    if not turbines:
        print("[ERROR] ДАННЫЕ ОТСУТСТВУЮТ")
        print("\nПричина:")
        print("  Данные не были загружены в БД")
        print("\nРешение:")
        print("  1. Запустить приложение")
        print("  2. На Home экране нажать 'Загрузить архив'")
        print("  3. Выбрать все .rd2 файлы из test_data")
        print("  4. Дождаться загрузки")
    elif not timeline:
        print("[ERROR] TIMELINE ПУСТ")
        print("\nПричина:")
        print("  Архивы есть, но record_datetime не заполнен")
        print("  Или даты архивов вне диапазона 120 дней")
    elif not spectrum_data:
        print("[ERROR] СПЕКТР ВЧ(ф) ПУСТ")
        print("\nПричина:")
        print("  Нет архивов с filter_type='HIGH' для датчика 3")
        print("  Или не вычисляется FFT")
    else:
        print("[OK] ВСЕ ДАННЫЕ ПРИСУТСТВУЮТ")
        print("  Графики должны отображаться корректно")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_upload_info_screen())
