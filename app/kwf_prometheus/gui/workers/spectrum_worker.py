# -*- coding: utf-8 -*-
"""
Воркер для асинхронной загрузки спектральных данных ВЧ(ф).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from PySide6.QtCore import QThread, Signal

from ...dal.repositories.base import IVibrationRepository
from ...dal.logger import get_logger

logger = get_logger(__name__)


class SpectrumDataWorker(QThread):
    """Воркер для загрузки данных ВЧ(ф) спектра по датчику."""

    data_ready = Signal(object)  # List[Tuple[datetime, float, float]] - (date, freq, amplitude)
    error = Signal(str)

    def __init__(self, repository: IVibrationRepository, wtg_id: str, 
                 sensor_id: int, months: int = 4, parent=None):
        """
        Args:
            repository: Репозиторий БД
            wtg_id: ID турбины (WTGxx)
            sensor_id: ID датчика (1-8)
            months: Количество месяцев для загрузки
        """
        super().__init__(parent)
        self.repository = repository
        self.wtg_id = wtg_id
        self.sensor_id = sensor_id
        self.months = months

    def run(self):
        """Выполнить асинхронный запрос к БД."""
        try:
            logger.debug(
                "Загрузка спектра ВЧ(ф) для %s, датчик %s (%s мес.)", 
                self.wtg_id, self.sensor_id, self.months
            )
            
            end_date = datetime.now()
            # Используем days=months*30, но не меньше 300 дней для тестовых данных
            days_count = max(self.months * 30, 300)
            start_date = end_date - timedelta(days=days_count)
            
            # Получаем спектральные данные
            data_points = asyncio.run(
                self.repository.get_vh_spectrum_data(
                    self.wtg_id,
                    self.sensor_id,
                    start_date,
                    end_date
                )
            )
            
            # Преобразуем в формат [(date, freq, amp), ...]
            result = []
            if data_points:
                for record in data_points:
                    # record = {'timestamp': datetime, 'frequency': float, 'amplitude': float}
                    dt = record.get('timestamp')
                    freq = record.get('frequency', 0.0)
                    amp = record.get('amplitude', 0.0)
                    if dt and freq is not None and amp is not None:
                        result.append((dt, freq, amp))
            
            logger.debug("Загружено %s точек спектра", len(result))
            self.data_ready.emit(result)
            
        except Exception as e:
            logger.error("Ошибка загрузки спектра: %s", e, exc_info=True)
            self.error.emit(str(e))
