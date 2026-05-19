# -*- coding: utf-8 -*-
"""
Базовый интерфейс репозитория.

Определяет контракт для всех реализаций репозиториев.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List


class IVibrationRepository(ABC):
    """
    Абстрактный репозиторий для доступа к данным вибрационной диагностики.
    
    Интерфейс определяет методы для:
    - Загрузки и парсинга архивов
    - Получения метрик турбины
    - Получения данных датчиков
    - Получения и сохранения результатов анализа
    """
    
    @abstractmethod
    async def load_archive(self, archive_path: Path) -> bool:
        """
        Загрузить архив с данными.
        
        Для FileSystemRepository: просто парсит файл и сохраняет в памяти.
        Для PostgresRepository: парсит и сохраняет данные в БД.
        
        Args:
            archive_path: Путь к файлу .zip или .rd2.
            
        Returns:
            True если загрузка успешна, False иначе.
        """
        pass
    
    @abstractmethod
    async def get_turbine_metrics(
        self,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить метрики турбины.
        
        Args:
            archive_path: Путь к архиву (для обратной совместимости).
            
        Returns:
            Словарь с метриками:
            - power_kw: Мощность (кВт)
            - generator_speed_rpm: Частота вращения (RPM)
            - wind_speed_ms: Скорость ветра (м/с)
            - cumulative_power_kwh: Накопленная выработка (кВт·ч)
        """
        pass
    
    @abstractmethod
    async def get_sensor_data(
        self,
        sensor_id: int,
        archive_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить данные для конкретного датчика.
        
        Args:
            sensor_id: Номер датчика (1-8).
            archive_path: Путь к архиву (для обратной совместимости).
            
        Returns:
            Словарь с данными датчика или None:
            - sensor_id: Номер датчика
            - acceleration: Временной ряд (НЧ)
            - acceleration_time: Временные метки
            - acceleration_fs: Частота дискретизации
            - velocity: Временной ряд (ВЧ)
            - velocity_time: Временные метки
            - velocity_fs: Частота дискретизации
            - high_freq: Временной ряд (ВЧ(ф))
            - high_freq_time: Временные метки
            - high_freq_fs: Частота дискретизации
        """
        pass
    
    @abstractmethod
    async def get_spectrum(
        self,
        sensor_id: int,
        filter_type: str,
        archive_path: Optional[str] = None
    ) -> Dict[str, List[float]]:
        """
        Получить спектр для датчика.
        
        Args:
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            archive_path: Путь к архиву (для обратной совместимости).
            
        Returns:
            Словарь со спектром:
            - frequencies: Список частот (Гц)
            - amplitudes: Список амплитуд
        """
        pass
    
    @abstractmethod
    async def get_analysis_results(
        self,
        sensor_id: int,
        filter_type: str,
        archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить результаты анализа для датчика.
        
        Args:
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            archive_path: Путь к архиву (для обратной совместимости).
            
        Returns:
            Словарь с результатами:
            - rms_total: Общее СКЗ
            - zone: Зона (A/B/C/D)
            - peak: Пиковое значение
            - peak_to_peak: Размах
            - peaks: Список пиков спектра
        """
        pass
    
    @abstractmethod
    async def save_analysis_results(
        self,
        sensor_id: int,
        filter_type: str,
        results: Dict[str, Any],
        archive_path: Optional[str] = None
    ) -> bool:
        """
        Сохранить результаты анализа в кэш.
        
        Args:
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            results: Результаты анализа.
            archive_path: Путь к архиву (для обратной совместимости).
            
        Returns:
            True если сохранение успешно.
        """
        pass
    
    @abstractmethod
    async def list_archives(self) -> List[Dict[str, Any]]:
        """
        Получить список доступных архивов.
        
        Returns:
            Список словарей с информацией об архивах:
            - turbine: Идентификатор турбины
            - date_str: Дата записи (строка)
            - size_kb: Размер файла (КБ)
            - path: Путь к файлу
        """
        pass
    
    @abstractmethod
    async def get_archive_parser(self, archive_path: str) -> Optional[Any]:
        """
        Получить объект парсера для обратной совместимости с UI.
        
        Args:
            archive_path: Путь к архиву.
            
        Returns:
            Объект MultiSensorRD2Parser или None.
        """
        pass
