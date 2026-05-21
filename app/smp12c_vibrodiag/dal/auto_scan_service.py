# -*- coding: utf-8 -*-
"""
Сервис автопарсинга иерархического хранилища.

AutoScanService периодически сканирует файловую систему,
находит новые ZIP-архивы и сохраняет их в БД через
DataPersistenceService.

Поддерживает структуру:
    Корневой_каталог/
        YYYYMM/
            DD/
                *SMP_RWD_*.zip
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from PySide6.QtCore import QThread, Signal

from .persistence_service import DataPersistenceService
from .logger import get_logger

logger = get_logger("AutoScanService")


class ScanResult:
    """Результат сканирования хранилища."""
    
    def __init__(self):
        self.total_found: int = 0
        self.processed: int = 0
        self.skipped: int = 0
        self.added_records: int = 0
        self.skipped_records: int = 0
        self.errors: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        """Длительность сканирования в секундах."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            'total_found': self.total_found,
            'processed': self.processed,
            'skipped': self.skipped,
            'added_records': self.added_records,
            'skipped_records': self.skipped_records,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds
        }


class AutoScanWorker(QThread):
    """
    Поток для фонового сканирования хранилища.
    
    Не блокирует GUI во время обработки архивов.
    """
    
    progress = Signal(int, int, int, int)  # found, processed, skipped, total
    archive_processed = Signal(str, int, int)  # path, added, skipped
    finished_scan = Signal(object)  # ScanResult
    error = Signal(str)
    
    def __init__(
        self,
        root_path: Path,
        persistence_service: DataPersistenceService,
        pattern: str = "*SMP_RWD_*.zip",
        max_depth: int = 5,
        parent=None
    ):
        super().__init__(parent)
        self.root_path = Path(root_path)
        self.persistence_service = persistence_service
        self.pattern = pattern
        self.max_depth = max_depth
        self._is_cancelled = False
    
    def cancel(self):
        """Отменить сканирование."""
        self._is_cancelled = True
    
    def run(self):
        """Запустить сканирование."""
        import asyncio
        
        result = ScanResult()
        result.start_time = datetime.utcnow()
        
        try:
            # Создаём event loop для async операций
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Находим все ZIP-архивы
                archives = self._find_archives()
                result.total_found = len(archives)
                
                logger.info(
                    "Начало сканирования: %s, найдено %d архивов",
                    self.root_path, len(archives)
                )
                
                # Обрабатываем каждый архив
                for i, archive_path in enumerate(archives):
                    if self._is_cancelled:
                        logger.info("Сканирование отменено")
                        break
                    
                    try:
                        # Обрабатываем архив
                        save_result = loop.run_until_complete(
                            self.persistence_service.save_archive(archive_path)
                        )
                        
                        if save_result.get('skipped') == -1:
                            # Архив уже был обработан ранее
                            result.skipped += 1
                        elif save_result.get('success'):
                            result.processed += 1
                            result.added_records += save_result.get('added', 0)
                            result.skipped_records += save_result.get('skipped', 0)
                            
                            # Сигнализируем о обработанном архиве
                            self.archive_processed.emit(
                                archive_path.name,
                                save_result.get('added', 0),
                                save_result.get('skipped', 0)
                            )
                        
                        if save_result.get('errors'):
                            result.errors.extend(save_result['errors'])
                        
                        # Отправляем прогресс
                        self.progress.emit(
                            result.total_found,
                            result.processed,
                            result.skipped,
                            i + 1
                        )
                        
                    except Exception as e:
                        msg = f"Ошибка обработки {archive_path.name}: {e}"
                        logger.error(msg)
                        result.errors.append(msg)
                
            finally:
                loop.close()
            
            result.end_time = datetime.utcnow()
            
            logger.info(
                "Сканирование завершено: найдено %d, обработано %d, "
                "пропущено %d, добавлено %d записей, за %.1f сек",
                result.total_found,
                result.processed,
                result.skipped,
                result.added_records,
                result.duration_seconds
            )
            
            self.finished_scan.emit(result)
            
        except Exception as e:
            msg = f"Критическая ошибка сканирования: {e}"
            logger.error(msg, exc_info=True)
            result.end_time = datetime.utcnow()
            result.errors.append(msg)
            self.error.emit(msg)
            self.finished_scan.emit(result)
    
    def _find_archives(self) -> List[Path]:
        """
        Найти все ZIP-архивы в хранилище.
        
        Returns:
            Список путей к архивам, отсортированный по имени.
        """
        archives = []
        
        if not self.root_path.exists():
            logger.warning("Корневой каталог не существует: %s", self.root_path)
            return archives
        
        # Используем rglob для рекурсивного поиска
        # Ограничиваем глубину через проверку
        for path in self.root_path.rglob(self.pattern):
            # Проверяем глубину вложенности
            relative = path.relative_to(self.root_path)
            depth = len(relative.parts) - 1  # -1 потому что сам файл
            
            if depth <= self.max_depth:
                archives.append(path)
        
        # Сортируем по пути (хронологический порядок)
        archives.sort()
        
        return archives


class AutoScanService:
    """
    Сервис автопарсинга хранилища.
    
    Управляет периодическим сканированием через QTimer.
    """
    
    def __init__(
        self,
        root_path: Path,
        persistence_service: DataPersistenceService,
        interval_minutes: int = 10,
        enabled: bool = True
    ):
        """
        Инициализация сервиса.
        
        Args:
            root_path: Корневой каталог хранилища.
            persistence_service: Сервис сохранения данных.
            interval_minutes: Интервал сканирования в минутах.
            enabled: Включено ли автопарсинг.
        """
        self.root_path = Path(root_path)
        self.persistence_service = persistence_service
        self.interval_minutes = interval_minutes
        self.enabled = enabled
        
        self._worker: Optional[AutoScanWorker] = None
        self._timer: Optional[Any] = None  # QTimer будет создан при подключении к GUI
        self._last_result: Optional[ScanResult] = None
    
    def start_timer(self, parent_widget):
        """
        Запустить периодический таймер.
        
        Args:
            parent_widget: Родительский виджет для QTimer.
        """
        from PySide6.QtCore import QTimer
        
        if not self.enabled:
            logger.info("Автопарсинг отключён в настройках")
            return
        
        self._timer = QTimer(parent_widget)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start(self.interval_minutes * 60 * 1000)  # мс
        
        logger.info(
            "Автопарсинг запущен: интервал %d мин, каталог %s",
            self.interval_minutes, self.root_path
        )
    
    def stop_timer(self):
        """Остановить таймер."""
        if self._timer:
            self._timer.stop()
            self._timer = None
            logger.info("Автопарсинг остановлен")
    
    def _on_timer_tick(self):
        """Обработчик срабатывания таймера."""
        logger.debug("Таймер автопарсинга: запуск сканирования")
        self.start_scan()
    
    def start_scan(
        self,
        on_progress: Optional[Callable] = None,
        on_archive: Optional[Callable] = None,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> AutoScanWorker:
        """
        Запустить однократное сканирование.
        
        Args:
            on_progress: Callback(found, processed, skipped, total).
            on_archive: Callback(archive_name, added, skipped).
            on_finished: Callback(ScanResult).
            on_error: Callback(error_msg).
            
        Returns:
            Запущенный worker.
        """
        # Останавливаем предыдущий worker если есть
        if self._worker and self._worker.isRunning():
            logger.warning("Предыдущее сканирование ещё выполняется, отменяем")
            self._worker.cancel()
            self._worker.wait(5000)
        
        # Создаём новый worker
        self._worker = AutoScanWorker(
            self.root_path,
            self.persistence_service
        )
        
        # Подключаем сигналы
        if on_progress:
            self._worker.progress.connect(on_progress)
        if on_archive:
            self._worker.archive_processed.connect(on_archive)
        if on_finished:
            self._worker.finished_scan.connect(on_finished)
        if on_error:
            self._worker.error.connect(on_error)
        
        # Сохраняем результат
        self._worker.finished_scan.connect(self._on_scan_finished)
        
        self._worker.start()
        logger.info("Сканирование запущено: %s", self.root_path)
        
        return self._worker
    
    def _on_scan_finished(self, result: ScanResult):
        """Обработка завершения сканирования."""
        self._last_result = result
        logger.info(
            "Сканирование завершено: %d найдено, %d обработано, "
            "%d добавлено записей",
            result.total_found,
            result.processed,
            result.added_records
        )
    
    def is_running(self) -> bool:
        """Проверить, выполняется ли сканирование."""
        return self._worker is not None and self._worker.isRunning()
    
    def get_last_result(self) -> Optional[ScanResult]:
        """Получить результат последнего сканирования."""
        return self._last_result
