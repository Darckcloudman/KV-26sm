# -*- coding: utf-8 -*-
"""
Единый сервис сохранения данных в БД.

DataPersistenceService — фасад над PostgresRepository,
обеспечивающий единый интерфейс для сохранения архивов
с дедупликацией и обработкой ошибок.
"""

import asyncio
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from .repositories.postgres import PostgresRepository
from .models import ProcessedArchive
from .database import DatabaseManager
from .logger import get_logger

logger = get_logger("DataPersistenceService")


class DataPersistenceService:
    """
    Единый сервис сохранения данных в PostgreSQL.
    
    Используется всеми точками входа:
    - GUI (кнопки, меню, Drag & Drop)
    - Автопарсинг (по таймеру)
    - Утилиты миграции (migrate_archives.py)
    """
    
    def __init__(self, repository: PostgresRepository):
        """
        Инициализация сервиса.
        
        Args:
            repository: Репозиторий PostgreSQL.
        """
        self.repository = repository
    
    async def save_archive(
        self,
        archive_path: Path,
        skip_processed_check: bool = False
    ) -> Dict[str, Any]:
        """
        Сохранить архив (.zip или .rd2) в БД.
        
        Для ZIP-архивов: распаковывает во временную папку и обрабатывает
        каждый .rd2 файл. Для одиночных .rd2 — сохраняет напрямую.
        
        Args:
            archive_path: Путь к файлу.
            skip_processed_check: Если True, не проверять таблицу processed_archives
                (используется при принудительной перезагрузке).
                
        Returns:
            Словарь с результатами:
            - success: bool
            - added: int — количество добавленных записей
            - skipped: int — количество пропущенных дубликатов
            - errors: List[str] — список ошибок
            - wtg_id: Optional[str] — идентификатор ВЭУ (если определён)
        """
        archive_path = Path(archive_path)
        result = {
            'success': False,
            'added': 0,
            'skipped': 0,
            'errors': [],
            'wtg_id': None
        }
        
        if not archive_path.exists():
            msg = f"Файл не найден: {archive_path}"
            logger.error(msg)
            result['errors'].append(msg)
            return result
        
        # Проверяем, не обрабатывали ли уже этот архив
        if not skip_processed_check and archive_path.suffix.lower() == '.zip':
            is_processed = await self._is_archive_processed(archive_path)
            if is_processed:
                logger.debug("Архив уже обработан ранее: %s", archive_path)
                result['success'] = True
                result['skipped'] = -1  # Специальное значение: пропущен полностью
                return result
        
        logger.info("Сохранение архива: %s", archive_path)
        
        try:
            if archive_path.suffix.lower() == '.zip':
                # Обрабатываем ZIP-архив
                zip_result = await self._process_zip_archive(archive_path)
                result.update(zip_result)
            elif archive_path.suffix.lower() == '.rd2':
                # Одиночный .rd2 файл — делегируем репозиторию
                repo_result = await self.repository.load_archive(archive_path)
                result.update(repo_result)
                if repo_result.get('success'):
                    # Извлекаем WTG ID из результата парсинга
                    result['wtg_id'] = await self._extract_wtg_from_archive(archive_path)
            else:
                msg = f"Неподдерживаемый формат файла: {archive_path.suffix}"
                logger.warning(msg)
                result['errors'].append(msg)
                return result
            
            # Сохраняем информацию об обработанном архиве
            if result['success'] and archive_path.suffix.lower() == '.zip':
                await self._mark_archive_processed(
                    archive_path,
                    result.get('wtg_id'),
                    result['added'],
                    result['skipped']
                )
            
            logger.info(
                "Архив сохранён: %s — добавлено %d, пропущено %d, ошибок %d",
                archive_path.name,
                result['added'],
                result['skipped'] if result['skipped'] >= 0 else 0,
                len(result['errors'])
            )
            
        except Exception as e:
            msg = f"Ошибка сохранения архива {archive_path}: {e}"
            logger.error(msg, exc_info=True)
            result['errors'].append(msg)
        
        return result
    
    async def _process_zip_archive(self, zip_path: Path) -> Dict[str, Any]:
        """
        Обработать ZIP-архив с несколькими .rd2 файлами.
        
        Args:
            zip_path: Путь к ZIP-архиву.
            
        Returns:
            Результаты обработки.
        """
        result = {'success': True, 'added': 0, 'skipped': 0, 'errors': [], 'wtg_id': None}
        
        # Создаём временную директорию
        temp_dir = Path(tempfile.mkdtemp(prefix="vibrodiag_"))
        
        try:
            # Распаковываем ZIP
            logger.debug("Распаковка ZIP: %s", zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            # Ищем все .rd2 файлы
            rd2_files = sorted(temp_dir.rglob("*.rd2"))
            
            if not rd2_files:
                msg = f"В архиве {zip_path.name} не найдены .rd2 файлы"
                logger.warning(msg)
                result['errors'].append(msg)
                return result
            
            logger.debug("Найдено %d .rd2 файлов в архиве", len(rd2_files))
            
            # Обрабатываем каждый .rd2 файл
            for rd2_file in rd2_files:
                try:
                    repo_result = await self.repository.load_archive(rd2_file)
                    
                    if repo_result.get('success'):
                        result['added'] += repo_result.get('added', 0)
                        result['skipped'] += repo_result.get('skipped', 0)
                        
                        # Извлекаем WTG ID (берём из первого успешного файла)
                        if result['wtg_id'] is None:
                            result['wtg_id'] = await self._extract_wtg_from_archive(rd2_file)
                    
                    result['errors'].extend(repo_result.get('errors', []))
                    
                except Exception as e:
                    msg = f"Ошибка обработки {rd2_file.name}: {e}"
                    logger.error(msg)
                    result['errors'].append(msg)
            
        except zipfile.BadZipFile:
            msg = f"Повреждённый ZIP-архив: {zip_path}"
            logger.error(msg)
            result['errors'].append(msg)
            result['success'] = False
        except Exception as e:
            msg = f"Ошибка распаковки {zip_path}: {e}"
            logger.error(msg, exc_info=True)
            result['errors'].append(msg)
            result['success'] = False
        finally:
            # Очищаем временную директорию
            try:
                shutil.rmtree(temp_dir)
                logger.debug("Временная директория удалена: %s", temp_dir)
            except Exception as e:
                logger.warning("Не удалось удалить временную директорию %s: %s", temp_dir, e)
        
        return result
    
    async def _is_archive_processed(self, archive_path: Path) -> bool:
        """
        Проверить, обрабатывался ли архив ранее.
        
        Сравнивает путь, размер и время модификации файла.
        
        Args:
            archive_path: Путь к архиву.
            
        Returns:
            True если архив уже обработан и не изменился.
        """
        try:
            stat = archive_path.stat()
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            
            async with self.repository.db_manager.session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(ProcessedArchive).where(
                        ProcessedArchive.file_path == str(archive_path)
                    )
                )
                processed = result.scalar_one_or_none()
                
                if processed is None:
                    return False
                
                # Проверяем, изменился ли файл
                if processed.file_size != current_size or processed.file_mtime != current_mtime:
                    logger.debug(
                        "Архив изменился: %s (size: %d->%d, mtime: %f->%f)",
                        archive_path.name,
                        processed.file_size, current_size,
                        processed.file_mtime, current_mtime
                    )
                    return False
                
                return True
                
        except Exception as e:
            logger.warning("Ошибка проверки processed_archives: %s", e)
            return False
    
    async def _mark_archive_processed(
        self,
        archive_path: Path,
        wtg_id: Optional[str],
        added: int,
        skipped: int
    ) -> None:
        """
        Отметить архив как обработанный.
        
        Args:
            archive_path: Путь к архиву.
            wtg_id: Идентификатор ВЭУ.
            added: Количество добавленных записей.
            skipped: Количество пропущенных дубликатов.
        """
        try:
            stat = archive_path.stat()
            
            async with self.repository.db_manager.session_factory() as session:
                from sqlalchemy import select
                
                # Ищем существующую запись
                result = await session.execute(
                    select(ProcessedArchive).where(
                        ProcessedArchive.file_path == str(archive_path)
                    )
                )
                processed = result.scalar_one_or_none()
                
                if processed:
                    # Обновляем существующую
                    processed.file_size = stat.st_size
                    processed.file_mtime = stat.st_mtime
                    processed.turbine_wtg_id = wtg_id
                    processed.records_added = added
                    processed.records_skipped = skipped
                    processed.processed_at = datetime.utcnow()
                else:
                    # Создаём новую
                    processed = ProcessedArchive(
                        file_path=str(archive_path),
                        file_size=stat.st_size,
                        file_mtime=stat.st_mtime,
                        turbine_wtg_id=wtg_id,
                        records_added=added,
                        records_skipped=skipped
                    )
                    session.add(processed)
                
                await session.commit()
                logger.debug("Архив отмечен как обработанный: %s", archive_path.name)
                
        except Exception as e:
            logger.error("Ошибка записи в processed_archives: %s", e)
    
    async def _extract_wtg_from_archive(self, archive_path: Path) -> Optional[str]:
        """
        Извлечь WTG ID из архива (для информации).
        
        Args:
            archive_path: Путь к .rd2 файлу.
            
        Returns:
            WTG ID или None.
        """
        try:
            from ...parsers.rd2_parser import MultiSensorRD2Parser
            parser = MultiSensorRD2Parser(str(archive_path))
            parser.parse()
            if parser.turbine_metadata:
                return parser.turbine_metadata.get('wtg_id')
        except Exception:
            pass
        return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Получить общую статистику обработки.
        
        Returns:
            Словарь с:
            - total_archives: всего обработанных архивов
            - total_records: всего добавленных записей
            - total_skipped: всего пропущенных дубликатов
            - last_processed: дата последней обработки
        """
        try:
            async with self.repository.db_manager.session_factory() as session:
                from sqlalchemy import select, func
                
                result = await session.execute(
                    select(
                        func.count(ProcessedArchive.id).label('total'),
                        func.sum(ProcessedArchive.records_added).label('added'),
                        func.sum(ProcessedArchive.records_skipped).label('skipped'),
                        func.max(ProcessedArchive.processed_at).label('last')
                    )
                )
                row = result.one()
                
                return {
                    'total_archives': row.total or 0,
                    'total_records': row.added or 0,
                    'total_skipped': row.skipped or 0,
                    'last_processed': row.last
                }
        except Exception as e:
            logger.error("Ошибка получения статистики: %s", e)
            return {
                'total_archives': 0,
                'total_records': 0,
                'total_skipped': 0,
                'last_processed': None
            }
