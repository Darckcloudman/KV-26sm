# -*- coding: utf-8 -*-
"""
Воркер для асинхронного получения статистики по ВЭУ.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QThread, Signal

from ...dal.repositories.base import IVibrationRepository
from ...dal.logger import get_logger

logger = get_logger(__name__)


class StatisticsWorker(QThread):
    """Воркер для загрузки статистики по турбине."""

    statistics_ready = Signal(object)  # Dict[str, Any] или None
    error = Signal(str)

    def __init__(self, repository: IVibrationRepository, wtg_id: str, 
                 months: int = 4, parent=None):
        """
        Args:
            repository: Репозиторий БД
            wtg_id: ID турбины (WTGxx)
            months: Количество месяцев для статистики (по умолчанию 4)
        """
        super().__init__(parent)
        self.repository = repository
        self.wtg_id = wtg_id
        self.months = months

    def run(self):
        """Выполнить асинхронный запрос к БД."""
        try:
            logger.debug("Загрузка статистики для %s (%s мес.)", self.wtg_id, self.months)
            
            # Получаем базовую статистику
            result = asyncio.run(
                self.repository.get_turbine_statistics(self.wtg_id)
            )
            
            if result:
                # Добавляем timeline за последние N месяцев
                end_date = datetime.now()
                start_date = end_date - timedelta(days=self.months * 30)
                
                timeline = asyncio.run(
                    self.repository.get_records_timeline(
                        self.wtg_id, 
                        start_date, 
                        end_date
                    )
                )
                result['records_timeline'] = timeline or {}
                result['timeline_start'] = start_date.strftime("%Y-%m-%d")
                result['timeline_end'] = end_date.strftime("%Y-%m-%d")
            
            self.statistics_ready.emit(result)
        except Exception as e:
            logger.error("Ошибка загрузки статистики: %s", e, exc_info=True)
            self.error.emit(str(e))
