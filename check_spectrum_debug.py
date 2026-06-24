# -*- coding: utf-8 -*-
"""
Проверка данных спектра ВЧ(ф) в БД
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def check_spectrum_data():
    """Проверить данные спектра в БД."""
    print("=" * 70)
    print("ПРОВЕРКА ДАННЫХ СПЕКТРА ВЧ(ф)")
    print("=" * 70)
    
    # Подключение к БД
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("\n[OK] БД подключена\n")
    
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    
    # Получаем список турбин
    turbines = await repo.list_turbines()
    if not turbines:
        print("[ERROR] В БД нет турбин")
        return
    
    print(f"Найдено турбин: {len(turbines)}")
    for t in turbines:
        print(f"  - {t['wtg_id']} (архивов: {t['total_archives']})")
    
    wtg_id = turbines[0]['wtg_id']
    
    # Проверяем каждый датчик
    for sensor_id in [2, 5, 7]:  # Датчики со скриншотов
        print(f"\n{'='*70}")
        print(f"ДАТЧИК {sensor_id}")
        print(f"{'='*70}")
        
        # Проверяем архивы
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        
        spectrum_data = await repo.get_vh_spectrum_data(
            wtg_id, sensor_id, start_date, end_date
        )
        
        if not spectrum_data:
            print(f"  [ERROR] Спектр пуст для датчика {sensor_id}")
        else:
            print(f"  [OK] Найдено точек спектра: {len(spectrum_data)}")
            
            # Группируем по датам
            from collections import defaultdict
            by_date = defaultdict(list)
            for point in spectrum_data:
                date_key = point['timestamp'].strftime("%Y-%m-%d") if point['timestamp'] else "Unknown"
                by_date[date_key].append(point)
            
            print(f"  Дат по записям: {len(by_date)}")
            for date, points in sorted(by_date.items()):
                print(f"    {date}: {len(points)} точек")
            
            # Проверяем диапазон частот и амплитуд
            freqs = [p['frequency'] for p in spectrum_data if p['frequency']]
            amps = [p['amplitude'] for p in spectrum_data if p['amplitude']]
            
            if freqs:
                print(f"  Частоты: мин={min(freqs):.2f} Гц, макс={max(freqs):.2f} Гц")
            if amps:
                print(f"  Амплитуды: мин={min(amps):.6f}, макс={max(amps):.6f}")
        
        # Проверяем наличие HIGH фильтров в БД
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
                print(f"  Архивов HIGH в БД: {count}")
    
    print(f"\n{'='*70}")
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(check_spectrum_data())
