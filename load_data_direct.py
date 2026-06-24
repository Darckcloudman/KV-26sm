# -*- coding: utf-8 -*-
"""
Прямая загрузка тестовых данных в БД (обход GUI)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.dal.config import settings
from kwf_prometheus.dal.database import DatabaseManager
from kwf_prometheus.dal.repositories.postgres import PostgresRepository


async def load_test_data():
    """Загрузить все .rd2 файлы из test_data."""
    print("=" * 70)
    print("ЗАГРУЗКА ТЕСТОВЫХ ДАННЫХ В БД")
    print("=" * 70)
    
    # Подключение к БД
    print("\n[1/3] Подключение к БД...")
    db_manager = DatabaseManager(settings)
    connected = await db_manager.connect_with_retry()
    
    if not connected:
        print("  [ERROR] Не удалось подключиться к БД")
        return
    
    print("  [OK] БД подключена")
    
    # Создание репозитория
    print("\n[2/3] Создание репозитория...")
    repo = PostgresRepository(db_manager, Path(settings.archive_storage_path))
    print("  [OK] Репозиторий создан")
    
    # Поиск файлов
    print("\n[3/3] Загрузка файлов...")
    test_data_path = Path("test_data")
    rd2_files = list(test_data_path.glob("*.rd2"))
    
    print(f"  Найдено файлов: {len(rd2_files)}")
    
    if len(rd2_files) == 0:
        print("  [ERROR] Файлы не найдены в test_data/")
        return
    
    # Загрузка каждого файла
    total_added = 0
    total_skipped = 0
    total_errors = 0
    
    for i, file_path in enumerate(rd2_files, 1):
        print(f"\n  [{i}/{len(rd2_files)}] {file_path.name}")
        
        try:
            result = await repo.load_archive(file_path)
            
            if result.get('success'):
                added = result.get('added', 0)
                skipped = result.get('skipped', 0)
                total_added += added
                total_skipped += skipped
                print(f"    [OK] Добавлено: {added}, Пропущено: {skipped}")
            else:
                errors = result.get('errors', [])
                total_errors += 1
                print(f"    [ERROR] {errors}")
                
        except Exception as e:
            total_errors += 1
            print(f"    [ERROR] Исключение: {e}")
    
    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ ЗАГРУЗКИ")
    print("=" * 70)
    print(f"Всего файлов: {len(rd2_files)}")
    print(f"Добавлено записей: {total_added}")
    print(f"Пропущено (дубликаты): {total_skipped}")
    print(f"Ошибок: {total_errors}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(load_test_data())
