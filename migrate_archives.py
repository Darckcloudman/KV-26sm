# -*- coding: utf-8 -*-
"""
Утилита для миграции существующих архивов в PostgreSQL.

Использование:
    python migrate_archives.py [--path PATH] [--dry-run]

Аргументы:
    --path PATH     Путь к каталогу с архивами (по умолчанию ./test_data)
    --dry-run       Показать что будет сделано, но не записывать в БД
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулю приложения
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smp12c_vibrodiag.dal.config import settings
from smp12c_vibrodiag.dal.database import DatabaseManager
from smp12c_vibrodiag.dal.repositories.postgres import PostgresRepository


async def migrate_archives(archive_dir: Path, dry_run: bool = False):
    """
    Мигрировать все архивы из каталога в PostgreSQL.
    
    Args:
        archive_dir: Путь к каталогу с архивами.
        dry_run: Если True, не записывать в БД.
    """
    if not settings.use_database:
        print("Ошибка: USE_DATABASE=false в .env")
        print("Установите USE_DATABASE=true для миграции.")
        return
    
    # Инициализация БД
    db_manager = DatabaseManager(settings)
    await db_manager.init_db()
    
    repository = PostgresRepository(
        db_manager=db_manager,
        archive_storage_path=archive_dir
    )
    
    # Находим все архивы
    archive_files = sorted(
        f for f in archive_dir.iterdir()
        if f.suffix.lower() in ('.zip', '.rd2')
    )
    
    if not archive_files:
        print(f"Архивы не найдены в {archive_dir}")
        return
    
    print(f"Найдено архивов: {len(archive_files)}")
    print(f"Режим: {'Тестовый (dry-run)' if dry_run else 'Запись в БД'}")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for i, archive_path in enumerate(archive_files, 1):
        print(f"[{i}/{len(archive_files)}] {archive_path.name}...", end=" ")
        
        if dry_run:
            print("[DRY-RUN: пропущено]")
            success_count += 1
            continue
        
        try:
            success = await repository.load_archive(archive_path)
            if success:
                print("[OK]")
                success_count += 1
            else:
                print("[УЖЕ В БД]")
                success_count += 1
        except Exception as e:
            print(f"[ОШИБКА: {e}]")
            error_count += 1
    
    print("-" * 60)
    print(f"Готово! Успешно: {success_count}, Ошибок: {error_count}")
    
    await db_manager.close()


def main():
    parser = argparse.ArgumentParser(
        description="Миграция архивов в PostgreSQL"
    )
    parser.add_argument(
        '--path',
        type=Path,
        default=settings.archive_storage_path,
        help='Путь к каталогу с архивами'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Тестовый режим без записи в БД'
    )
    
    args = parser.parse_args()
    
    asyncio.run(migrate_archives(args.path, args.dry_run))


if __name__ == "__main__":
    main()
