# -*- coding: utf-8 -*-
"""
Репозиторий для работы с PostgreSQL.

Использует SQLAlchemy 2.0 async для хранения и чтения данных.
При загрузке архива парсит и сохраняет данные в БД.
При последующих запросах читает из БД.
"""

import hashlib
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from ...parsers.rd2_parser import MultiSensorRD2Parser
from ..database import DatabaseManager
from ..models import Turbine, Archive, SensorData, AnalysisCache
from ..logger import get_logger
from .base import IVibrationRepository

logger = get_logger("PostgresRepository")


def _with_retry(max_retries: int = 3, delay: float = 1.0):
    """
    Декоратор для повторных попыток при временных сбоях БД.
    
    Args:
        max_retries: Максимальное количество попыток.
        delay: Задержка между попытками в секундах.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(self, *args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    logger.warning(
                        "Ошибка БД в %s (попытка %d/%d): %s",
                        func.__name__, attempt, max_retries, e
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
                except SQLAlchemyError as e:
                    last_exception = e
                    logger.error(
                        "SQLAlchemy ошибка в %s: %s",
                        func.__name__, e, exc_info=True
                    )
                    raise
            logger.error(
                "Исчерпаны попытки в %s после %d попыток",
                func.__name__, max_retries
            )
            raise last_exception
        return wrapper
    return decorator


class PostgresRepository(IVibrationRepository):
    """
    Репозиторий PostgreSQL.
    
    Хранит распарсенные данные в БД для быстрого доступа.
    Использует кэширование результатов анализа.
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        archive_storage_path: Path
    ):
        """
        Инициализация репозитория.
        
        Args:
            db_manager: Менеджер подключений к БД.
            archive_storage_path: Путь к каталогу с архивами.
        """
        self.db_manager = db_manager
        self.archive_storage_path = Path(archive_storage_path)
        self._current_archive_id: Optional[int] = None
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Вычислить SHA256 хэш файла."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @_with_retry(max_retries=3, delay=1.0)
    async def load_archive(self, archive_path: Path) -> Dict[str, Any]:
        """
        Загрузить архив в базу данных с дедупликацией.
        
        Для каждого .rd2 файла в архиве проверяет уникальность по ключу:
        (turbine_id, record_datetime, sensor_id, filter_type)
        
        Args:
            archive_path: Путь к файлу .zip или .rd2.
            
        Returns:
            Словарь с результатами:
            - success: bool — общий успех
            - added: int — количество добавленных записей
            - skipped: int — количество пропущенных дубликатов
            - errors: List[str] — список ошибок
        """
        result = {'success': False, 'added': 0, 'skipped': 0, 'errors': []}
        
        logger.info("Загрузка архива: %s", archive_path)
        try:
            archive_path = Path(archive_path)
            if not archive_path.exists():
                logger.error("Файл не найден: %s", archive_path)
                result['errors'].append(f"Файл не найден: {archive_path}")
                return result
            
            # Парсим файл
            logger.debug("Парсинг файла...")
            parser = await asyncio.to_thread(
                self._parse_archive_sync, archive_path
            )
            
            if not parser or not parser._parsed:
                logger.error("Не удалось распарсить файл: %s", archive_path)
                result['errors'].append("Не удалось распарсить файл")
                return result
            
                # Получаем метаданные прибора
                metadata = parser.turbine_metadata or {}
                wtg_id = metadata.get('wtg_id', 'Unknown')
                sensor_serial = metadata.get('sensor_serial')  # v1.4: серийный номер датчика
                
                device_info = {
                'device': metadata.get('device'),
                'serial_number': metadata.get('device_serial'),
                'mac_address': metadata.get('mac_address'),
                'ip_address': metadata.get('ip_address'),
                'firmware_version': metadata.get('firmware_version'),
            }
            
            logger.debug(
                "Метаданные прибора: device=%s, serial=%s, mac=%s, ip=%s",
                device_info['device'],
                device_info['serial_number'],
                device_info['mac_address'],
                device_info['ip_address']
            )
            
            async with self.db_manager.session_factory() as session:
                # Получаем или создаём турбину (с проверкой serial/mac)
                try:
                    turbine = await self._get_or_create_turbine(
                        session, wtg_id, device_info
                    )
                except ValueError as e:
                    logger.error("Ошибка привязки прибора: %s", e)
                    result['errors'].append(str(e))
                    return result
                
                # Парсим дату-время записи
                record_datetime = self._parse_record_datetime(
                    metadata.get('record_datetime', '')
                )
                
                # Получаем метрики турбины
                metrics = parser.get_turbine_metrics()
                file_size_kb = archive_path.stat().st_size // 1024
                
                # Обрабатываем каждый датчик и фильтр
                filter_map = {
                    'FILTER': 'acceleration',
                    'LOW': 'velocity',
                    'HIGH': 'high_freq'
                }
                
                for sensor_id in range(1, 9):
                    data = parser.get_sensor_data(sensor_id)
                    if data is None:
                        continue
                    
                    for filter_type, signal_key in filter_map.items():
                        values = data.get(signal_key)
                        if values is None or len(values) == 0:
                            continue
                        
                        # Проверяем дедупликацию по уникальному ключу
                        existing = await self._find_archive_by_unique_key(
                            session, turbine.id, record_datetime, 
                            sensor_id, filter_type
                        )
                        
                        if existing:
                            logger.debug(
                                "Пропуск дубликата: turbine=%s, datetime=%s, "
                                "sensor=%d, filter=%s",
                                wtg_id, record_datetime, sensor_id, filter_type
                            )
                            result['skipped'] += 1
                            continue
                        
                        # Создаём запись архива
                        archive = Archive(
                            turbine_id=turbine.id,
                            file_path=str(archive_path),
                            file_hash="",  # Хэш не используется как основной критерий
                            record_datetime=record_datetime,
                            file_size_kb=file_size_kb,
                            power_kw=metrics.get('power_kw', 0.0),
                            generator_speed_rpm=metrics.get('generator_speed_rpm', 0.0),
                            wind_speed_ms=metrics.get('wind_speed_ms', 0.0),
                            cumulative_power_kwh=metrics.get('cumulative_power_kwh', 0.0),
                            sensor_id=sensor_id,
                            filter_type=filter_type,
                            sensor_serial=sensor_serial  # v1.4
                        )
                        session.add(archive)
                        await session.flush()  # Получаем ID
                        
                        # Сохраняем данные датчика
                        timestamps = data.get(f"{signal_key}_time")
                        fs = data.get(f"{signal_key}_fs")
                        
                        sensor_data = SensorData(
                            archive_id=archive.id,
                            sensor_id=sensor_id,
                            filter_type=filter_type,
                            timestamps=timestamps.tolist() if hasattr(timestamps, 'tolist') else list(timestamps),
                            values=values.tolist() if hasattr(values, 'tolist') else list(values),
                            sampling_frequency=float(fs) if fs else 25600.0,
                            samples_count=len(values)
                        )
                        session.add(sensor_data)
                
                        result['added'] += 1
                        logger.debug(
                            "Добавлена запись: id=%d, sensor=%d, filter=%s",
                            archive.id, sensor_id, filter_type
                        )
                
                await session.commit()
                result['success'] = True
                
                logger.info(
                    "Архив загружен: %s — добавлено %d, пропущено %d",
                    archive_path.name, result['added'], result['skipped']
                )
                return result
                
        except Exception as e:
            logger.error("Ошибка загрузки архива в БД: %s", e, exc_info=True)
            result['errors'].append(str(e))
            return result
    
    def _parse_archive_sync(self, archive_path: Path) -> MultiSensorRD2Parser:
        """Синхронный парсинг файла."""
        parser = MultiSensorRD2Parser(str(archive_path))
        parser.parse()
        return parser
    
    async def _get_or_create_turbine(
        self,
        session: AsyncSession,
        wtg_id: str,
        device_info: Optional[Dict[str, str]] = None
    ) -> Turbine:
        """
        Получить или создать турбину по WTG и данным прибора.
        
        Порядок поиска:
        1. По serial_number (главный идентификатор прибора)
        2. По mac_address (резервный идентификатор)
        3. По wtg_id (если прибор ещё не зарегистрирован)
        
        Args:
            session: Сессия БД
            wtg_id: Идентификатор турбины
            device_info: Словарь с полями прибора (serial_number, mac_address, ip_address, device, firmware_version)
            
        Returns:
            Объект Turbine
            
        Raises:
            ValueError: Если serial привязан к другому wtg_id
        """
        device_info = device_info or {}
        serial_number = device_info.get('serial_number')
        mac_address = device_info.get('mac_address')
        
        # 1. Ищем по serial_number (главный идентификатор)
        if serial_number:
            result = await session.execute(
                select(Turbine).where(Turbine.serial_number == serial_number)
            )
            turbine = result.scalar_one_or_none()
            if turbine:
                # Проверяем консистентность wtg_id
                if turbine.wtg_id != wtg_id:
                    raise ValueError(
                        f"Несоответствие: прибор с серийным номером {serial_number} "
                        f"уже привязан к турбине {turbine.wtg_id}, "
                        f"но текущий файл содержит турбину {wtg_id}. "
                        f"Загрузка отменена."
                    )
                # Обновляем изменяемые поля
                if mac_address:
                    turbine.mac_address = mac_address
                if device_info.get('ip_address'):
                    turbine.ip_address = device_info['ip_address']
                if device_info.get('firmware_version'):
                    turbine.firmware_version = device_info['firmware_version']
                return turbine
        
        # 2. Ищем по mac_address (резервный идентификатор)
        if mac_address:
            result = await session.execute(
                select(Turbine).where(Turbine.mac_address == mac_address)
            )
            turbine = result.scalar_one_or_none()
            if turbine:
                # Проверяем консистентность wtg_id
                if turbine.wtg_id != wtg_id:
                    raise ValueError(
                        f"Несоответствие: прибор с MAC {mac_address} "
                        f"уже привязан к турбине {turbine.wtg_id}, "
                        f"но текущий файл содержит турбину {wtg_id}. "
                        f"Загрузка отменена."
                    )
                # Обновляем serial_number и другие поля
                if serial_number:
                    turbine.serial_number = serial_number
                if device_info.get('ip_address'):
                    turbine.ip_address = device_info['ip_address']
                if device_info.get('firmware_version'):
                    turbine.firmware_version = device_info['firmware_version']
                return turbine
        
        # 3. Ищем по wtg_id
        result = await session.execute(
            select(Turbine).where(Turbine.wtg_id == wtg_id)
        )
        turbine = result.scalar_one_or_none()
        
        if turbine:
            # Обновляем данные прибора (если раньше не было)
            if serial_number and not turbine.serial_number:
                turbine.serial_number = serial_number
            if mac_address and not turbine.mac_address:
                turbine.mac_address = mac_address
            if device_info.get('device') and not turbine.device:
                turbine.device = device_info['device']
            if device_info.get('ip_address'):
                turbine.ip_address = device_info['ip_address']
            if device_info.get('firmware_version'):
                turbine.firmware_version = device_info['firmware_version']
            return turbine
        
        # 4. Создаём новую турбину
        turbine = Turbine(
            wtg_id=wtg_id,
            name=wtg_id,
            device=device_info.get('device'),
            serial_number=serial_number,
            mac_address=mac_address,
            ip_address=device_info.get('ip_address'),
            firmware_version=device_info.get('firmware_version')
        )
        session.add(turbine)
        await session.flush()
        logger.info("Создана новая турбина: %s (serial=%s, mac=%s)", wtg_id, serial_number, mac_address)
        return turbine
    
    async def _find_archive_by_unique_key(
        self,
        session: AsyncSession,
        turbine_id: int,
        record_datetime: Optional[datetime],
        sensor_id: int,
        filter_type: str
    ) -> Optional[Archive]:
        """
        Проверить существование записи по логическому ключу.
        
        Уникальный ключ: (turbine_id, record_datetime, sensor_id, filter_type)
        
        Returns:
            Archive если найден, None если нет
        """
        if not record_datetime:
            return None
            
        result = await session.execute(
            select(Archive).where(
                and_(
                    Archive.turbine_id == turbine_id,
                    Archive.record_datetime == record_datetime,
                    Archive.sensor_id == sensor_id,
                    Archive.filter_type == filter_type
                )
            )
        )
        return result.scalar_one_or_none()
                
    def _parse_record_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Парсить дату-время из метаданных."""
        if not datetime_str:
            return None
        
        # Форматы: "2025-09-01 12:00:00" или "20250901_120000"
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d_%H%M%S",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    async def _save_sensor_data(
        self,
        session: AsyncSession,
        archive_id: int,
        parser: MultiSensorRD2Parser
    ) -> None:
        """Сохранить данные датчиков в БД."""
        filter_map = {
            'FILTER': 'acceleration',
            'LOW': 'velocity',
            'HIGH': 'high_freq'
        }
        
        for sensor_id in range(1, 9):
            data = parser.get_sensor_data(sensor_id)
            if data is None:
                continue
            
            for filter_type, signal_key in filter_map.items():
                values = data.get(signal_key)
                timestamps = data.get(f"{signal_key}_time")
                fs = data.get(f"{signal_key}_fs")
                
                if values is None or len(values) == 0:
                    continue
                
                sensor_data = SensorData(
                    archive_id=archive_id,
                    sensor_id=sensor_id,
                    filter_type=filter_type,
                    timestamps=timestamps.tolist() if hasattr(timestamps, 'tolist') else list(timestamps),
                    values=values.tolist() if hasattr(values, 'tolist') else list(values),
                    sampling_frequency=float(fs) if fs else 25600.0,
                    samples_count=len(values)
                )
                session.add(sensor_data)
                
    @_with_retry(max_retries=3, delay=1.0)
    async def get_turbine_metrics(
        self,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить метрики турбины из БД."""
        if self._current_archive_id is None:
            logger.warning("get_turbine_metrics: archive_id не установлен")
            return {
                'power_kw': 0.0,
                'generator_speed_rpm': 0.0,
                'wind_speed_ms': 0.0,
                'cumulative_power_kwh': 0.0
            }
        
        logger.debug("Получение метрик турбины (archive_id=%d)", self._current_archive_id)
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(Archive).where(Archive.id == self._current_archive_id)
            )
            archive = result.scalar_one_or_none()
            
            if archive is None:
                logger.warning("Архив id=%d не найден в БД", self._current_archive_id)
                return {
                    'power_kw': 0.0,
                    'generator_speed_rpm': 0.0,
                    'wind_speed_ms': 0.0,
                    'cumulative_power_kwh': 0.0
                }
            
            metrics = {
                'power_kw': archive.power_kw or 0.0,
                'generator_speed_rpm': archive.generator_speed_rpm or 0.0,
                'wind_speed_ms': archive.wind_speed_ms or 0.0,
                'cumulative_power_kwh': archive.cumulative_power_kwh or 0.0
            }
            logger.debug("Метрики турбины: %s", metrics)
            return metrics
    
    async def get_sensor_data(
        self,
        sensor_id: int,
        archive_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Получить данные датчика из БД."""
        if self._current_archive_id is None:
            return None
        
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(SensorData).where(
                    and_(
                        SensorData.archive_id == self._current_archive_id,
                        SensorData.sensor_id == sensor_id
                    )
                )
            )
            sensor_records = result.scalars().all()
            
            if not sensor_records:
                return None
            
            # Формируем результат как в оригинальном парсере
            result_data = {
                'sensor_id': sensor_id,
                'acceleration': None,
                'acceleration_time': None,
                'acceleration_fs': None,
                'velocity': None,
                'velocity_time': None,
                'velocity_fs': None,
                'high_freq': None,
                'high_freq_time': None,
                'high_freq_fs': None,
            }
            
            filter_map = {
                'FILTER': 'acceleration',
                'LOW': 'velocity',
                'HIGH': 'high_freq'
            }
            
            for record in sensor_records:
                signal_key = filter_map.get(record.filter_type)
                if signal_key:
                    result_data[signal_key] = record.values
                    result_data[f"{signal_key}_time"] = record.timestamps
                    result_data[f"{signal_key}_fs"] = record.sampling_frequency
            
            return result_data
    
    async def get_spectrum(
        self,
        sensor_id: int,
        filter_type: str,
        archive_path: Optional[str] = None
    ) -> Dict[str, List[float]]:
        """Получить спектр из кэша или вычислить."""
        if self._current_archive_id is None:
            return {'frequencies': [], 'amplitudes': []}
        
        # Проверяем кэш
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(AnalysisCache).where(
                    and_(
                        AnalysisCache.archive_id == self._current_archive_id,
                        AnalysisCache.sensor_id == sensor_id,
                        AnalysisCache.filter_type == filter_type
                    )
                )
            )
            cached = result.scalar_one_or_none()
            
            if cached and cached.spectrum_frequencies:
                return {
                    'frequencies': cached.spectrum_frequencies,
                    'amplitudes': cached.spectrum_amplitudes
                }
        
        # Вычисляем спектр
        sensor_data = await self.get_sensor_data(sensor_id, archive_path)
        if sensor_data is None:
            return {'frequencies': [], 'amplitudes': []}
        
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
        
        # Вычисляем FFT
        return await asyncio.to_thread(
            self._calculate_spectrum_sync, values, fs
        )
    
    def _calculate_spectrum_sync(
        self,
        values: List[float],
        sampling_freq: float
    ) -> Dict[str, List[float]]:
        """Синхронное вычисление спектра."""
        import numpy as np
        
        values_array = np.array(values)
        n = len(values_array)
        fft_result = np.fft.rfft(values_array)
        frequencies = np.fft.rfftfreq(n, d=1/sampling_freq)
        amplitudes = np.abs(fft_result) * 2 / n
        
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
        """Получить результаты анализа из кэша или вычислить."""
        if self._current_archive_id is None:
            return {
                'rms_total': 0.0,
                'zone': 'A',
                'peak': 0.0,
                'peak_to_peak': 0.0,
                'peaks': []
            }
        
        # Проверяем кэш
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(AnalysisCache).where(
                    and_(
                        AnalysisCache.archive_id == self._current_archive_id,
                        AnalysisCache.sensor_id == sensor_id,
                        AnalysisCache.filter_type == filter_type
                    )
                )
            )
            cached = result.scalar_one_or_none()
            
            if cached and cached.rms_total is not None:
                return {
                    'rms_total': cached.rms_total,
                    'zone': cached.zone,
                    'peak': cached.peak,
                    'peak_to_peak': cached.peak_to_peak,
                    'peaks': cached.peaks or []
                }
        
        # Вычисляем результаты
        sensor_data = await self.get_sensor_data(sensor_id, archive_path)
        if sensor_data is None:
            return {
                'rms_total': 0.0,
                'zone': 'A',
                'peak': 0.0,
                'peak_to_peak': 0.0,
                'peaks': []
            }
        
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
        
        return await asyncio.to_thread(self._analyze_sync, values)
    
    def _analyze_sync(self, values: List[float]) -> Dict[str, Any]:
        """Синхронный анализ сигнала."""
        import numpy as np
        
        values_array = np.array(values)
        rms = np.sqrt(np.mean(values_array ** 2))
        zone = self._determine_zone(rms)
        peak = float(np.max(np.abs(values_array)))
        peak_to_peak = float(np.max(values_array) - np.min(values_array))
        
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
        """Сохранить результаты анализа в кэш."""
        if self._current_archive_id is None:
            return False
        
        try:
            async with self.db_manager.session_factory() as session:
                # Проверяем, есть ли уже кэш
                result = await session.execute(
                    select(AnalysisCache).where(
                        and_(
                            AnalysisCache.archive_id == self._current_archive_id,
                            AnalysisCache.sensor_id == sensor_id,
                            AnalysisCache.filter_type == filter_type
                        )
                    )
                )
                cached = result.scalar_one_or_none()
                
                if cached:
                    # Обновляем существующий кэш
                    cached.rms_total = results.get('rms_total')
                    cached.zone = results.get('zone')
                    cached.peak = results.get('peak')
                    cached.peak_to_peak = results.get('peak_to_peak')
                    cached.peaks = results.get('peaks')
                    cached.analyzed_at = datetime.utcnow()
                else:
                    # Создаём новый кэш
                    cache = AnalysisCache(
                        archive_id=self._current_archive_id,
                        sensor_id=sensor_id,
                        filter_type=filter_type,
                        rms_total=results.get('rms_total'),
                        zone=results.get('zone'),
                        peak=results.get('peak'),
                        peak_to_peak=results.get('peak_to_peak'),
                        peaks=results.get('peaks')
                    )
                    session.add(cache)
                
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка сохранения результатов в БД: {e}")
            return False
    
    async def list_archives(self) -> List[Dict[str, Any]]:
        """Получить список архивов из БД."""
        archives = []
        
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(Archive).order_by(Archive.record_datetime.desc())
            )
            db_archives = result.scalars().all()
            
            for archive in db_archives:
                # Получаем информацию о турбине
                result = await session.execute(
                    select(Turbine).where(Turbine.id == archive.turbine_id)
                )
                turbine = result.scalar_one_or_none()
                
                date_str = (
                    archive.record_datetime.strftime("%d.%m.%Y %H:%M")
                    if archive.record_datetime else "—"
                )
                
                archives.append({
                    'turbine': turbine.wtg_id if turbine else "Unknown",
                    'date_str': date_str,
                    'size_kb': f"{archive.file_size_kb} КБ",
                    'path': archive.file_path
                })
        
        return archives
    
    async def get_archive_parser(
        self,
        archive_path: str
    ) -> Optional[MultiSensorRD2Parser]:
        """
        Получить парсер для обратной совместимости.
        
        Для PostgreSQL создаём парсер на лету из данных БД.
        """
        # Для совместимости с UI создаём парсер из файла
        return await asyncio.to_thread(self._parse_archive_sync, Path(archive_path))

    # === Методы для работы с ветропарком (v1.4) ===

    async def list_turbines(self) -> List[Dict[str, Any]]:
        """Получить список всех ВЭУ."""
        turbines = []
        
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(Turbine).order_by(Turbine.wtg_id)
            )
            db_turbines = result.scalars().all()
            
            for turbine in db_turbines:
                # Считаем количество архивов
                count_result = await session.execute(
                    select(Archive).where(Archive.turbine_id == turbine.id)
                )
                total_archives = len(count_result.scalars().all())
                
                turbines.append({
                    'wtg_id': turbine.wtg_id,
                    'name': turbine.name or turbine.wtg_id,
                    'total_archives': total_archives
                })
        
        logger.info("Получено %d турбин", len(turbines))
        return turbines

    @_with_retry(max_retries=3, delay=1.0)
    async def get_turbine_statistics(self, wtg_id: str) -> Optional[Dict[str, Any]]:
        """Получить статистику по конкретной ВЭУ."""
        logger.debug("Получение статистики для ВЭУ: %s", wtg_id)
        
        async with self.db_manager.session_factory() as session:
            # Находим турбину
            result = await session.execute(
                select(Turbine).where(Turbine.wtg_id == wtg_id)
            )
            turbine = result.scalar_one_or_none()
            
            if turbine is None:
                logger.warning("Турбина %s не найдена", wtg_id)
                return None
            
            # Получаем все архивы турбины
            archives_result = await session.execute(
                select(Archive)
                .where(Archive.turbine_id == turbine.id)
                .order_by(Archive.record_datetime.desc())
            )
            archives = archives_result.scalars().all()
            
            if not archives:
                return {
                    'total_archives': 0,
                    'first_record': None,
                    'last_record': None,
                    'avg_rms_per_sensor': {},
                    'trend_last_10': [],
                    'critical_count': 0
                }
            
            # Диапазон дат
            first_record = archives[-1].record_datetime if archives else None
            last_record = archives[0].record_datetime if archives else None
            
            # Критические записи (зона D)
            critical_count = 0
            
            # Средний RMS по датчикам
            avg_rms_per_sensor = {i: [] for i in range(1, 9)}
            
            # Последние 10 записей для тренда
            trend_last_10 = []
            
            for archive in archives[:50]:  # Ограничиваем для производительности
                # Получаем результаты анализа
                analysis_result = await session.execute(
                    select(AnalysisCache).where(
                        AnalysisCache.archive_id == archive.id
                    )
                )
                analyses = analysis_result.scalars().all()
                
                for analysis in analyses:
                    if analysis.rms_total:
                        avg_rms_per_sensor[analysis.sensor_id].append(analysis.rms_total)
                    
                    # Считаем критические
                    if analysis.zone == 'D':
                        critical_count += 1
                
                # Для тренда берём датчик 1, фильтр LOW
                sensor_1_low = next(
                    (a for a in analyses if a.sensor_id == 1 and a.filter_type == 'LOW'),
                    None
                )
                if sensor_1_low and sensor_1_low.rms_total:
                    trend_last_10.append({
                        'date': archive.record_datetime.isoformat() if archive.record_datetime else None,
                        'rms_total': sensor_1_low.rms_total
                    })
            
            # Усредняем RMS
            avg_rms_per_sensor = {
                sensor_id: sum(values) / len(values) if values else 0.0
                for sensor_id, values in avg_rms_per_sensor.items()
            }
            
            # Берём последние 10 точек тренда
            trend_last_10 = trend_last_10[:10]
            
            stats = {
                'total_archives': len(archives),
                'first_record': first_record,
                'last_record': last_record,
                'avg_rms_per_sensor': avg_rms_per_sensor,
                'trend_last_10': trend_last_10,
                'critical_count': critical_count
            }
            
            logger.debug("Статистика для %s: %d архивов, критических: %d", wtg_id, len(archives), critical_count)
            return stats

    @_with_retry(max_retries=3, delay=1.0)
    async def get_rms_trend(
        self,
        wtg_id: Optional[str] = None,
        sensor_id: int = 1,
        filter_type: str = "LOW"
    ) -> List[Dict[str, Any]]:
        """
        Получить тренд RMS по времени.
        
        Если wtg_id is None — агрегируем по всем турбинам (среднее по парку).
        """
        logger.debug("Получение тренда RMS: wtg_id=%s, sensor=%d, filter=%s", wtg_id, sensor_id, filter_type)
        
        async with self.db_manager.session_factory() as session:
            if wtg_id:
                # Конкретная турбина
                result = await session.execute(
                    select(Turbine).where(Turbine.wtg_id == wtg_id)
                )
                turbine = result.scalar_one_or_none()
                
                if turbine is None:
                    return []
                
                # Получаем тренд для конкретной турбины
                trend_result = await session.execute(
                    select(AnalysisCache, Archive)
                    .join(Archive, AnalysisCache.archive_id == Archive.id)
                    .where(
                        and_(
                            Archive.turbine_id == turbine.id,
                            AnalysisCache.sensor_id == sensor_id,
                            AnalysisCache.filter_type == filter_type,
                            AnalysisCache.rms_total.isnot(None)
                        )
                    )
                    .order_by(Archive.record_datetime.asc())
                )
                
                trend_data = []
                for analysis, archive in trend_result.all():
                    if analysis.rms_total:
                        trend_data.append({
                            'date': archive.record_datetime.isoformat() if archive.record_datetime else None,
                            'rms_total': analysis.rms_total,
                            'wtg_id': wtg_id
                        })
                
                return trend_data
            else:
                # Агрегация по всему парку (группировка по дате)
                from sqlalchemy import func

                trend_result = await session.execute(
                    select(
                        func.date(Archive.record_datetime).label('date'),
                        func.avg(AnalysisCache.rms_total).label('avg_rms'),
                        func.count(AnalysisCache.id).label('count')
                    )
                    .join(Archive, AnalysisCache.archive_id == Archive.id)
                    .where(
                        and_(
                            AnalysisCache.sensor_id == sensor_id,
                            AnalysisCache.filter_type == filter_type,
                            AnalysisCache.rms_total.isnot(None)
                        )
                    )
                    .group_by(func.date(Archive.record_datetime))
                    .order_by(func.date(Archive.record_datetime).asc())
                )
                
                trend_data = []
                for date, avg_rms, count in trend_result.all():
                    if avg_rms:
                        trend_data.append({
                            'date': date.isoformat() if date else None,
                            'rms_total': float(avg_rms),
                            'wtg_id': 'AVG_ALL'
                        })
                
                return trend_data
