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
    async def load_archive(self, archive_path: Path) -> Dict[str, Any]:
        """
        Загрузить архив с данными.
        
        Для FileSystemRepository: просто парсит файл и сохраняет в памяти.
        Для PostgresRepository: парсит и сохраняет данные в БД с дедупликацией.
        
        Args:
            archive_path: Путь к файлу .zip или .rd2.
            
        Returns:
            Словарь с результатами:
            - success: bool — общий успех
            - added: int — количество добавленных записей
            - skipped: int — количество пропущенных дубликатов
            - errors: List[str] — список ошибок
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

    # === Методы для работы с ветропарком (v1.4) ===

    @abstractmethod
    async def list_turbines(self) -> List[Dict[str, Any]]:
        """
        Получить список всех ВЭУ (турбин).
        
        Returns:
            Список словарей:
            - wtg_id: Идентификатор (например, 'WTG37')
            - name: Название/описание
            - total_archives: Количество записей
        """
        pass

    @abstractmethod
    async def get_turbine_statistics(self, wtg_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить статистику по конкретной ВЭУ.
        
        Args:
            wtg_id: Идентификатор турбины (например, 'WTG37').
            
        Returns:
            Словарь со статистикой:
            - total_archives: Общее количество записей
            - first_record: Дата первой записи
            - last_record: Дата последней записи
            - avg_rms_per_sensor: Средний RMS по датчикам
            - trend_last_10: Список последних 10 записей (date, rms)
            - critical_count: Количество записей в зоне D
        """
        pass

    @abstractmethod
    async def get_rms_trend(
        self,
        wtg_id: Optional[str] = None,
        sensor_id: int = 1,
        filter_type: str = "LOW"
    ) -> List[Dict[str, Any]]:
        """
        Получить тренд RMS по времени.
        
        Args:
            wtg_id: Идентификатор турбины (None для агрегации по всему парку).
            sensor_id: Номер датчика (1-8).
            filter_type: Тип фильтра (FILTER/LOW/HIGH).
            
        Returns:
            Список точек {date, rms_total} для построения графика.
        """
        pass

    @abstractmethod
    async def get_records_timeline(
        self,
        wtg_id: str,
        start_date: Any,
        end_date: Any
    ) -> Optional[Dict[str, int]]:
        """
        Получить количество записей по дням за период.
        
        Args:
            wtg_id: Идентификатор турбины (например, 'WTG37').
            start_date: Начальная дата (datetime).
            end_date: Конечная дата (datetime).
            
        Returns:
            Словарь {date_str: count} где date_str в формате "YYYY-MM-DD".
        """
        pass

    @abstractmethod
    async def get_vh_spectrum_data(
        self,
        wtg_id: str,
        sensor_id: int,
        start_date: Any,
        end_date: Any,
        max_points: int = 5000
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Получить данные ВЧ(ф) спектра для 3D визуализации.
        
        Args:
            wtg_id: Идентификатор турбины.
            sensor_id: Номер датчика (1-8).
            start_date: Начальная дата.
            end_date: Конечная дата.
            max_points: Максимальное количество точек (для оптимизации).
            
        Returns:
            Список записей:
            - timestamp: datetime записи
            - frequency: частота (Гц)
            - amplitude: амплитуда (мм/с²)
        """
        pass
