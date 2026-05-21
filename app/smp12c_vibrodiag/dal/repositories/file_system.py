# -*- coding: utf-8 -*-
"""
Репозиторий для работы с файловой системой.

Сохраняет текущее поведение v1.2 - работает напрямую
с MultiSensorRD2Parser, не использует БД.
"""

import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from ...parsers.rd2_parser import MultiSensorRD2Parser
from .base import IVibrationRepository


class FileSystemRepository(IVibrationRepository):
    """
    Репозиторий файловой системы.
    
    Работает напрямую с парсером .zip/.rd2 файлов.
    Хранит данные в памяти (текущее поведение v1.2).
    """
    
    def __init__(self, archive_storage_path: Path):
        """
        Инициализация репозитория.
        
        Args:
            archive_storage_path: Путь к каталогу с архивами.
        """
        self.archive_storage_path = Path(archive_storage_path)
        self._current_parser: Optional[MultiSensorRD2Parser] = None
        self._current_file: Optional[str] = None
    
    async def load_archive(self, archive_path: Path) -> Dict[str, Any]:
        """
        Загрузить архив через парсер.
        
        Args:
            archive_path: Путь к файлу .zip или .rd2.
            
        Returns:
            Словарь с результатами:
            - success: bool
            - added: int (всегда 1 для файлового режима)
            - skipped: int (всегда 0)
            - errors: List[str]
        """
        try:
            # Запускаем парсинг в отдельном потоке (для неблокировки GUI)
            parser = await asyncio.to_thread(
                self._parse_archive_sync, archive_path
            )
            
            if parser and parser._parsed:
                self._current_parser = parser
                self._current_file = str(archive_path)
                return {'success': True, 'added': 1, 'skipped': 0, 'errors': []}
            return {'success': False, 'added': 0, 'skipped': 0, 'errors': ['Парсинг не удался']}
            
        except Exception as e:
            print(f"Ошибка загрузки архива: {e}")
            return {'success': False, 'added': 0, 'skipped': 0, 'errors': [str(e)]}
    
    def _parse_archive_sync(self, archive_path: Path) -> MultiSensorRD2Parser:
        """Синхронный парсинг (вызывается через asyncio.to_thread)."""
        parser = MultiSensorRD2Parser(str(archive_path))
        parser.parse()
        return parser
    
    async def get_turbine_metrics(
        self,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить метрики турбины из текущего парсера.
        
        Args:
            archive_path: Не используется (для совместимости).
            
        Returns:
            Метрики турбины.
        """
        if self._current_parser is None:
            return {
                'power_kw': 0.0,
                'generator_speed_rpm': 0.0,
                'wind_speed_ms': 0.0,
                'cumulative_power_kwh': 0.0
            }
        
        return await asyncio.to_thread(
            self._current_parser.get_turbine_metrics
        )
    
    async def get_sensor_data(
        self,
        sensor_id: int,
        archive_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить данные датчика.
        
        Args:
            sensor_id: Номер датчика (1-8).
            archive_path: Не используется (для совместимости).
            
        Returns:
            Данные датчика или None.
        """
        if self._current_parser is None:
            return None
        
        return await asyncio.to_thread(
            self._current_parser.get_sensor_data, sensor_id
        )
    
    async def get_spectrum(
        self,
        sensor_id: int,
        filter_type: str,
        archive_path: Optional[str] = None
    ) -> Dict[str, List[float]]:
        """
        Вычислить спектр для датчика.
        
        Args:
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            archive_path: Не используется (для совместимости).
            
        Returns:
            Словарь со спектром (частоты, амплитуды).
        """
        # Получаем данные датчика
        sensor_data = await self.get_sensor_data(sensor_id, archive_path)
        if sensor_data is None:
            return {'frequencies': [], 'amplitudes': []}
        
        # Определяем какой сигнал использовать
        signal_map = {
            'FILTER': ('acceleration', 'acceleration_fs'),
            'LOW': ('velocity', 'velocity_fs'),
            'HIGH': ('high_freq', 'high_freq_fs'),
        }
        
        signal_key, fs_key = signal_map.get(filter_type, (None, None))
        if signal_key is None:
            return {'frequencies': [], 'amplitudes': []}
        
        values = sensor_data.get(signal_key)
        fs = sensor_data.get(fs_key, 25600)
        
        if values is None or len(values) == 0:
            return {'frequencies': [], 'amplitudes': []}
        
        # Вычисляем FFT в отдельном потоке
        return await asyncio.to_thread(
            self._calculate_spectrum_sync, values, fs
        )
    
    def _calculate_spectrum_sync(
        self,
        values,
        sampling_freq: float
    ) -> Dict[str, List[float]]:
        """Синхронное вычисление спектра."""
        import numpy as np
        
        n = len(values)
        fft_result = np.fft.rfft(values)
        frequencies = np.fft.rfftfreq(n, d=1/sampling_freq)
        amplitudes = np.abs(fft_result) * 2 / n
        
        # Убираем DC компоненту
        return {
            'frequencies': frequencies[1:].tolist(),
            'amplitudes': amplitudes[1:].tolist()
        }
    
    async def get_analysis_results(
        self,
        sensor_id: int,
        filter_type: str,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Вычислить результаты анализа.
        
        Args:
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            archive_path: Не используется (для совместимости).
            
        Returns:
            Результаты анализа (RMS, зона, пики).
        """
        # Получаем данные датчика
        sensor_data = await self.get_sensor_data(sensor_id, archive_path)
        if sensor_data is None:
            return {
                'rms_total': 0.0,
                'zone': 'A',
                'peak': 0.0,
                'peak_to_peak': 0.0,
                'peaks': []
            }
        
        # Определяем сигнал
        signal_map = {
            'FILTER': 'acceleration',
            'LOW': 'velocity',
            'HIGH': 'high_freq',
        }
        signal_key = signal_map.get(filter_type)
        values = sensor_data.get(signal_key)
        
        if values is None or len(values) == 0:
            return {
                'rms_total': 0.0,
                'zone': 'A',
                'peak': 0.0,
                'peak_to_peak': 0.0,
                'peaks': []
            }
        
        # Вычисляем в отдельном потоке
        return await asyncio.to_thread(
            self._analyze_sync, values
        )
    
    def _analyze_sync(self, values) -> Dict[str, Any]:
        """Синхронный анализ сигнала."""
        import numpy as np
        
        # RMS
        rms = np.sqrt(np.mean(values ** 2))
        
        # Зона
        zone = self._determine_zone(rms)
        
        # Пиковое значение
        peak = float(np.max(np.abs(values)))
        peak_to_peak = float(np.max(values) - np.min(values))
        
        return {
            'rms_total': float(rms),
            'zone': zone,
            'peak': peak,
            'peak_to_peak': peak_to_peak,
            'peaks': []
        }
    
    def _determine_zone(self, rms_value: float) -> str:
        """Определить зону состояния по ISO 10816."""
        if rms_value < 2.3:
            return 'A'
        elif rms_value < 4.5:
            return 'B'
        elif rms_value < 7.8:
            return 'C'
        else:
            return 'D'
    
    async def save_analysis_results(
        self,
        sensor_id: int,
        filter_type: str,
        results: Dict[str, Any],
        archive_path: Optional[str] = None
    ) -> bool:
        """
        Сохранить результаты анализа.
        
        Для FileSystemRepository ничего не делает (нет БД).
        
        Args:
            sensor_id: Номер датчика.
            filter_type: Тип фильтра.
            results: Результаты анализа.
            archive_path: Не используется.
            
        Returns:
            True (для совместимости).
        """
        # Для файловой системы кэширование не требуется
        return True
    
    async def list_archives(self) -> List[Dict[str, Any]]:
        """
        Получить список архивов из каталога.
        
        Returns:
            Список архивов с метаданными.
        """
        archives = []
        
        if not self.archive_storage_path.exists():
            return archives
        
        for f in sorted(self.archive_storage_path.iterdir()):
            try:
                if f.suffix.lower() in ('.zip', '.rd2'):
                    size_kb = f.stat().st_size / 1024
                    date_str = self._extract_date_from_filename(f.name)
                    turbine = self._extract_turbine_from_filename(f.name)
                    archives.append({
                        'turbine': turbine,
                        'date_str': date_str,
                        'size_kb': f"{size_kb:.0f} КБ",
                        'path': str(f)
                    })
            except Exception:
                continue
        
        return archives
    
    def _extract_date_from_filename(self, filename: str) -> str:
        """Извлечь дату из имени файла."""
        match = re.search(r'(\d{8})', filename)
        if match:
            d = match.group(1)
            return f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
        try:
            mtime = (self.archive_storage_path / filename).stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
        except Exception:
            return "—"
    
    def _extract_turbine_from_filename(self, filename: str) -> str:
        """Извлечь идентификатор турбины из имени файла."""
        match = re.search(r'(WTG\d+|W\d+)', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return "Unknown"
    
    async def get_archive_parser(
        self,
        archive_path: str
    ) -> Optional[MultiSensorRD2Parser]:
        """
        Получить текущий парсер для обратной совместимости.
        
        Args:
            archive_path: Путь к архиву.
            
        Returns:
            Объект MultiSensorRD2Parser или None.
        """
        if self._current_file == archive_path and self._current_parser is not None:
            return self._current_parser
        
        # Загружаем если нужно
        success = await self.load_archive(Path(archive_path))
        if success:
            return self._current_parser
        return None

    # === Методы для работы с ветропарком (v1.4) ===
    # В файловом режиме статистика и тренды недоступны

    async def list_turbines(self) -> List[Dict[str, Any]]:
        """В файловом режиме — пустой список."""
        return []

    async def get_turbine_statistics(self, wtg_id: str) -> Optional[Dict[str, Any]]:
        """В файловом режиме — недоступно."""
        return None

    async def get_rms_trend(
        self,
        wtg_id: Optional[str] = None,
        sensor_id: int = 1,
        filter_type: str = "LOW"
    ) -> List[Dict[str, Any]]:
        """В файловом режиме — пустой список."""
        return []
