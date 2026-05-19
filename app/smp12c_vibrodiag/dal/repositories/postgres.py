# -*- coding: utf-8 -*-
"""
Репозиторий для работы с PostgreSQL.

Использует SQLAlchemy 2.0 async для хранения и чтения данных.
При загрузке архива парсит и сохраняет данные в БД.
При последующих запросах читает из БД.
"""

import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...parsers.rd2_parser import MultiSensorRD2Parser
from ..database import DatabaseManager
from ..models import Turbine, Archive, SensorData, AnalysisCache
from .base import IVibrationRepository


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
    
    async def load_archive(self, archive_path: Path) -> bool:
        """
        Загрузить архив в базу данных.
        
        Если архив уже загружен (по хэшу), возвращает True.
        Иначе парсит файл и сохраняет данные в БД.
        
        Args:
            archive_path: Путь к файлу .zip или .rd2.
            
        Returns:
            True если загрузка успешна.
        """
        try:
            archive_path = Path(archive_path)
            if not archive_path.exists():
                return False
            
            # Вычисляем хэш файла
            file_hash = await asyncio.to_thread(
                self._compute_file_hash, archive_path
            )
            file_size_kb = archive_path.stat().st_size // 1024
            
            async with self.db_manager.session_factory() as session:
                # Проверяем, есть ли уже такой архив
                result = await session.execute(
                    select(Archive).where(Archive.file_hash == file_hash)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Архив уже загружен
                    self._current_archive_id = existing.id
                    return True
                
                # Парсим файл
                parser = await asyncio.to_thread(
                    self._parse_archive_sync, archive_path
                )
                
                if not parser or not parser._parsed:
                    return False
                
                # Получаем или создаём турбину
                wtg_id = parser.turbine_metadata.get('wtg_id', 'Unknown')
                turbine = await self._get_or_create_turbine(session, wtg_id)
                
                # Создаём запись архива
                record_datetime = self._parse_record_datetime(
                    parser.turbine_metadata.get('record_datetime', '')
                )
                
                archive = Archive(
                    turbine_id=turbine.id,
                    file_path=str(archive_path),
                    file_hash=file_hash,
                    record_datetime=record_datetime,
                    file_size_kb=file_size_kb
                )
                session.add(archive)
                await session.flush()  # Получаем ID
                
                # Сохраняем данные датчиков
                await self._save_sensor_data(session, archive.id, parser)
                
                await session.commit()
                self._current_archive_id = archive.id
                return True
                
        except Exception as e:
            print(f"Ошибка загрузки архива в БД: {e}")
            return False
    
    def _parse_archive_sync(self, archive_path: Path) -> MultiSensorRD2Parser:
        """Синхронный парсинг файла."""
        parser = MultiSensorRD2Parser(str(archive_path))
        parser.parse()
        return parser
    
    async def _get_or_create_turbine(
        self,
        session: AsyncSession,
        wtg_id: str
    ) -> Turbine:
        """Получить или создать турбину."""
        result = await session.execute(
            select(Turbine).where(Turbine.wtg_id == wtg_id)
        )
        turbine = result.scalar_one_or_none()
        
        if turbine is None:
            turbine = Turbine(wtg_id=wtg_id)
            session.add(turbine)
            await session.flush()
        
        return turbine
    
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
    
    async def get_turbine_metrics(
        self,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить метрики турбины из БД."""
        if self._current_archive_id is None:
            return {
                'power_kw': 0.0,
                'generator_speed_rpm': 0.0,
                'wind_speed_ms': 0.0,
                'cumulative_power_kwh': 0.0
            }
        
        async with self.db_manager.session_factory() as session:
            result = await session.execute(
                select(Archive).where(Archive.id == self._current_archive_id)
            )
            archive = result.scalar_one_or_none()
            
            if archive is None:
                return {
                    'power_kw': 0.0,
                    'generator_speed_rpm': 0.0,
                    'wind_speed_ms': 0.0,
                    'cumulative_power_kwh': 0.0
                }
            
            # Получаем данные первого датчика для метрик
            result = await session.execute(
                select(SensorData).where(
                    and_(
                        SensorData.archive_id == self._current_archive_id,
                        SensorData.sensor_id == 1
                    )
                ).limit(1)
            )
            sensor_data = result.scalar_one_or_none()
            
            # Если данных в БД нет, возвращаем нули
            # (в реальности метрики должны храниться отдельно)
            return {
                'power_kw': 0.0,
                'generator_speed_rpm': 0.0,
                'wind_speed_ms': 0.0,
                'cumulative_power_kwh': 0.0
            }
    
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
