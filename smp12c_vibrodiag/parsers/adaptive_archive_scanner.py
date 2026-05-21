# -*- coding: utf-8 -*-
"""
Адаптивный сканер хранилища архивов SMP12C VibroDiag Analyzer v1.4

Сканирует файловую систему рекурсивно, находит ZIP-архивы по гибким паттернам,
анализирует содержимое и извлекает метаданные для сохранения в БД.

Поддерживаемые паттерны имён архивов:
- WTG\d+ (например, WTG6, WTG35)
- W\d{4} (например, W1436)
- SMP_RWD, SMP_RW, SMP_ (признак архива SMP12C)
- Дата в формате YYYYMMDD

Структура хранилища (ожидаемая):
    Корневой_каталог/
        YYYYMM/
            DD/
                W1436 WTG6 SMP_RWD_20250903.zip
"""

import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from ..dal.logger import get_logger

logger = get_logger("AdaptiveArchiveScanner")


@dataclass
class ArchiveCandidate:
    """Кандидат на обработку — найденный архив с метаданными."""
    path: Path                    # Полный путь к архиву
    filename: str                 # Имя файла
    wtg_id: Optional[str] = None  # WTG идентификатор (WTG1...WTG57)
    turbine_id: Optional[str] = None  # Идентификатор турбины (W1436)
    record_date: Optional[str] = None  # Дата записи (YYYYMMDD)
    record_datetime: Optional[datetime] = None  # Полная дата-время
    file_size_kb: int = 0         # Размер файла в КБ
    sensors_found: List[int] = field(default_factory=list)  # Найденные датчики (1-8)
    filter_types: Dict[int, List[str]] = field(default_factory=dict)  # Датчик -> [FILTER, LOW, HIGH]
    rd2_files_count: int = 0      # Количество .rd2 файлов внутри
    errors: List[str] = field(default_factory=list)  # Ошибки при анализе
    matched_pattern: str = ""     # Какой паттерн сработал
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            'path': str(self.path),
            'filename': self.filename,
            'wtg_id': self.wtg_id,
            'turbine_id': self.turbine_id,
            'record_date': self.record_date,
            'record_datetime': self.record_datetime.isoformat() if self.record_datetime else None,
            'file_size_kb': self.file_size_kb,
            'sensors_found': self.sensors_found,
            'filter_types': self.filter_types,
            'rd2_files_count': self.rd2_files_count,
            'errors': self.errors,
            'matched_pattern': self.matched_pattern
        }


class AdaptiveArchiveScanner:
    """
    Адаптивный сканер хранилища архивов.
    
    Рекурсивно обходит каталоги, находит ZIP-архивы по гибким паттернам,
    анализирует содержимое и возвращает структурированные данные.
    """
    
    # Паттерны для идентификации архивов
    ARCHIVE_PATTERNS = [
        # WTG + дата
        (r'WTG(\d{1,2}).*?(\d{8})', 'wtg_date'),
        # W#### + WTG + дата
        (r'W(\d{4}).*?WTG(\d{1,2}).*?(\d{8})', 'w_wtg_date'),
        # SMP_RWD + дата
        (r'SMP_RWD.*?(\d{8})', 'smp_rwd_date'),
        # SMP_RW + дата
        (r'SMP_RW.*?(\d{8})', 'smp_rw_date'),
        # Просто дата в имени
        (r'(\d{8})', 'date_only'),
    ]
    
    # Паттерны для имён файлов внутри архива
    SENSOR_PATTERN = re.compile(r'SENSOR_(\d{2})', re.IGNORECASE)
    FILTER_PATTERN = re.compile(r'(_FILTER_|_LOW_|_HIGH_)', re.IGNORECASE)
    
    def __init__(
        self,
        root_path: Path,
        max_depth: int = 6,
        min_depth: int = 0,
        custom_patterns: Optional[List[Tuple[str, str]]] = None
    ):
        """
        Инициализация сканера.
        
        Args:
            root_path: Корневой каталог для сканирования.
            max_depth: Максимальная глубина вложенности (относительно root_path).
            min_depth: Минимальная глубина вложенности.
            custom_patterns: Дополнительные паттерны для поиска архивов.
        """
        self.root_path = Path(root_path)
        self.max_depth = max_depth
        self.min_depth = min_depth
        self.patterns = self.ARCHIVE_PATTERNS + (custom_patterns or [])
        
        # Компилируем паттерны для эффективности
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.patterns
        ]
    
    def scan(self) -> List[ArchiveCandidate]:
        """
        Выполнить сканирование хранилища.
        
        Returns:
            Список ArchiveCandidate с найденными архивами.
        """
        logger.info("Начало сканирования хранилища: %s", self.root_path)
        
        if not self.root_path.exists():
            logger.error("Корневой каталог не существует: %s", self.root_path)
            return []
        
        candidates = []
        
        # Находим все ZIP-архивы
        zip_files = self._find_zip_files()
        logger.info("Найдено %d ZIP-архивов для анализа", len(zip_files))
        
        # Анализируем каждый архив
        for i, zip_path in enumerate(zip_files):
            try:
                candidate = self._analyze_archive(zip_path)
                if candidate:
                    candidates.append(candidate)
                    logger.debug(
                        "[%d/%d] Обработан архив: %s (WTG=%s, датчики=%d)",
                        i + 1, len(zip_files), zip_path.name,
                        candidate.wtg_id, len(candidate.sensors_found)
                    )
            except Exception as e:
                logger.error("Ошибка анализа архива %s: %s", zip_path, e)
        
        logger.info(
            "Сканирование завершено: %d архивов проанализировано",
            len(candidates)
        )
        
        return candidates
    
    def _find_zip_files(self) -> List[Path]:
        """
        Найти все ZIP-архивы в хранилище.
        
        Returns:
            Список путей к ZIP-файлам, отсортированный по пути.
        """
        zip_files = []
        
        # Рекурсивный обход с ограничением глубины
        for path in self.root_path.rglob("*.zip"):
            try:
                relative = path.relative_to(self.root_path)
                depth = len(relative.parts) - 1
                
                if self.min_depth <= depth <= self.max_depth:
                    zip_files.append(path)
            except ValueError:
                # Файл не в root_path (не должно случиться с rglob)
                continue
        
        # Сортируем по пути (хронологический порядок)
        zip_files.sort()
        
        return zip_files
    
    def _analyze_archive(self, archive_path: Path) -> Optional[ArchiveCandidate]:
        """
        Проанализировать ZIP-архив.
        
        Args:
            archive_path: Путь к ZIP-архиву.
            
        Returns:
            ArchiveCandidate или None если архив не соответствует критериям.
        """
        filename = archive_path.name
        candidate = ArchiveCandidate(
            path=archive_path,
            filename=filename,
            file_size_kb=archive_path.stat().st_size // 1024
        )
        
        # Проверяем имя файла на соответствие паттернам
        if not self._match_filename(filename, candidate):
            logger.debug("Архив не соответствует паттернам: %s", filename)
            return None
        
        # Анализируем содержимое архива
        try:
            self._analyze_zip_contents(archive_path, candidate)
        except zipfile.BadZipFile as e:
            candidate.errors.append(f"Повреждённый ZIP-архив: {e}")
            logger.warning("Повреждённый архив: %s", archive_path)
        except Exception as e:
            candidate.errors.append(f"Ошибка анализа содержимого: {e}")
            logger.error("Ошибка анализа архива %s: %s", archive_path, e)
        
        return candidate
    
    def _match_filename(self, filename: str, candidate: ArchiveCandidate) -> bool:
        """
        Проверить имя файла на соответствие паттернам.
        
        Args:
            filename: Имя файла.
            candidate: Объект для заполнения метаданными.
            
        Returns:
            True если файл соответствует хотя бы одному паттерну.
        """
        for pattern, pattern_name in self._compiled_patterns:
            match = pattern.search(filename)
            if match:
                candidate.matched_pattern = pattern_name
                groups = match.groups()
                
                # Извлекаем WTG ID
                if pattern_name == 'wtg_date':
                    candidate.wtg_id = f"WTG{int(groups[0])}"
                    candidate.record_date = groups[1]
                elif pattern_name == 'w_wtg_date':
                    candidate.turbine_id = f"W{groups[0]}"
                    candidate.wtg_id = f"WTG{int(groups[1])}"
                    candidate.record_date = groups[2]
                elif pattern_name in ('smp_rwd_date', 'smp_rw_date', 'date_only'):
                    candidate.record_date = groups[0]
                
                # Парсим дату
                if candidate.record_date:
                    try:
                        candidate.record_datetime = datetime.strptime(
                            candidate.record_date, "%Y%m%d"
                        )
                    except ValueError:
                        pass
                
                logger.debug(
                    "Паттерн '%s' сработал для %s: WTG=%s, дата=%s",
                    pattern_name, filename, candidate.wtg_id, candidate.record_date
                )
                return True
        
        return False
    
    def _analyze_zip_contents(
        self,
        archive_path: Path,
        candidate: ArchiveCandidate
    ):
        """
        Анализировать содержимое ZIP-архива.
        
        Args:
            archive_path: Путь к архиву.
            candidate: Объект для заполнения метаданными.
        """
        with zipfile.ZipFile(archive_path, 'r') as zf:
            # Находим все .rd2 файлы
            rd2_files = [f for f in zf.namelist() if f.lower().endswith('.rd2')]
            candidate.rd2_files_count = len(rd2_files)
            
            if not rd2_files:
                candidate.errors.append("В архиве не найдено файлов .rd2")
                return
            
            # Анализируем каждый .rd2 файл
            sensors = set()
            filter_types: Dict[int, set] = {}
            
            for rd2_file in rd2_files:
                # Извлекаем номер датчика
                sensor_match = self.SENSOR_PATTERN.search(rd2_file)
                if sensor_match:
                    sensor_id = int(sensor_match.group(1))
                    sensors.add(sensor_id)
                    
                    if sensor_id not in filter_types:
                        filter_types[sensor_id] = set()
                    
                    # Извлекаем тип фильтра
                    filter_match = self.FILTER_PATTERN.search(rd2_file)
                    if filter_match:
                        filter_str = filter_match.group(1).upper()
                        if '_FILTER_' in filter_str or '_LOW_W' in filter_str:
                            # Различаем FILTER и LOW
                            if 'LOW' in rd2_file.upper() and 'FILTER' not in rd2_file.upper():
                                filter_types[sensor_id].add('LOW')
                            else:
                                filter_types[sensor_id].add('FILTER')
                        elif '_HIGH_' in filter_str:
                            filter_types[sensor_id].add('HIGH')
            
            candidate.sensors_found = sorted(sensors)
            candidate.filter_types = {
                sensor_id: sorted(ftypes)
                for sensor_id, ftypes in filter_types.items()
            }
            
            logger.debug(
                "Архив %s: %d датчиков, %d .rd2 файлов",
                archive_path.name, len(sensors), len(rd2_files)
            )
    
    def scan_with_callback(
        self,
        on_archive_found: Optional[callable] = None,
        on_progress: Optional[callable] = None,
        on_error: Optional[callable] = None
    ) -> List[ArchiveCandidate]:
        """
        Сканирование с callback-ами для прогресса.
        
        Args:
            on_archive_found: Callback(candidate: ArchiveCandidate) для каждого архива.
            on_progress: Callback(current: int, total: int) для прогресса.
            on_error: Callback(error_msg: str) для ошибок.
            
        Returns:
            Список ArchiveCandidate.
        """
        logger.info("Начало сканирования с callback-ами: %s", self.root_path)
        
        if not self.root_path.exists():
            if on_error:
                on_error(f"Корневой каталог не существует: {self.root_path}")
            return []
        
        zip_files = self._find_zip_files()
        total = len(zip_files)
        candidates = []
        
        for i, zip_path in enumerate(zip_files):
            try:
                candidate = self._analyze_archive(zip_path)
                if candidate:
                    candidates.append(candidate)
                    if on_archive_found:
                        on_archive_found(candidate)
            except Exception as e:
                error_msg = f"Ошибка анализа {zip_path.name}: {e}"
                logger.error(error_msg)
                if on_error:
                    on_error(error_msg)
            
            if on_progress:
                on_progress(i + 1, total)
        
        logger.info("Сканирование завершено: %d архивов", len(candidates))
        return candidates


def extract_wtg_from_filename(filename: str) -> Optional[str]:
    """
    Извлечь WTG ID из имени файла (вспомогательная функция).
    
    Args:
        filename: Имя файла.
        
    Returns:
        WTG ID (например, 'WTG6') или None.
    """
    match = re.search(r'WTG(\d{1,2})', filename, re.IGNORECASE)
    if match:
        return f"WTG{int(match.group(1))}"
    return None


def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Извлечь дату из имени файла (вспомогательная функция).
    
    Args:
        filename: Имя файла.
        
    Returns:
        Дата в формате YYYYMMDD или None.
    """
    match = re.search(r'(\d{8})', filename)
    if match:
        return match.group(1)
    return None
