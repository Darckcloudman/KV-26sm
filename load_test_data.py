# -*- coding: utf-8 -*-
"""
Скрипт загрузки тестовых данных в БД.
Загружает все .rd2 файлы из test_data через DataPersistenceService.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository
from kwf_prometheus.dal.persistence_service import DataPersistenceService


async def load_test_data():
    """Загрузить тестовые данные в БД."""
    print("=" * 60)
    print("ЗАГРУЗКА ТЕСТОВЫХ ДАННЫХ")
    print("=" * 60)
    
    # Инициализация БД
    db_manager = DatabaseManager(settings)
    print("\nПодключение к БД...")
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("[ERROR] Не удалось подключиться к БД")
        return
    
    print("[OK] Подключение успешно!")
    
    # Создаём репозиторий и сервис
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    persistence_service = DataPersistenceService(repo)
    
    # Находим все .rd2 файлы
    test_data_path = Path(settings.archive_storage_path)
    rd2_files = list(test_data_path.glob("*.rd2"))
    
    print(f"\nНайдено файлов .rd2: {len(rd2_files)}")
    
    if not rd2_files:
        print("[WARNING] Файлы не найдены в", test_data_path)
        return
    
    # Загружаем файлы
    success_count = 0
    error_count = 0
    skip_count = 0
    
    for i, rd2_file in enumerate(rd2_files[:50], 1):  # Максимум 50 файлов
        print(f"\n[{i}/{len(rd2_files)}] {rd2_file.name}")
        
        try:
            result = await persistence_service.save_archive(rd2_file)
            
            if result.success:
                print(f"  [OK] Загружено: {result.added} записей, пропущено: {result.skipped}")
                if result.wtg_id:
                    print(f"  WTG: {result.wtg_id}")
                success_count += 1
            else:
                if result.errors:
                    print(f"  [WARNING] Ошибки: {result.errors[:200]}")
                skip_count += 1
                
        except Exception as e:
            print(f"  [ERROR] {e}")
            error_count += 1
    
    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ЗАГРУЗКИ")
    print("=" * 60)
    print(f"Всего файлов: {len(rd2_files)}")
    print(f"✅ Успешно: {success_count}")
    print(f"⏭️  Пропущено: {skip_count}")
    print(f"❌ Ошибки: {error_count}")
    
    # Проверка данных в БД
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ДАННЫХ В БД")
    print("=" * 60)
    
    turbines = await repo.list_turbines()
    print(f"Турбин в БД: {len(turbines)}")
    
    if turbines:
        for t in turbines:
            print(f"\n  {t['wtg_id']}:")
            print(f"    Архивов: {t.get('total_archives', 0)}")
            print(f"    Мощность: {t.get('power_kw', 'N/A')} кВт")
            print(f"    Скорость: {t.get('generator_speed_rpm', 'N/A')} RPM")
    
    print("\n" + "=" * 60)
    print("ГОТОВО")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(load_test_data())
