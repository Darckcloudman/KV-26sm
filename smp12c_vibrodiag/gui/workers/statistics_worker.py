# -*- coding: utf-8 -*-
"""
Воркер для асинхронного получения статистики по ВЭУ.
"""

import asyncio
from PySide6.QtCore import QThread, Signal

from ...dal.repositories.base import IVibrationRepository
from ...dal.logger import get_logger

logger = get_logger(__name__)


class StatisticsWorker(QThread):
    """Воркер для загрузки статистики по турбине."""

    statistics_ready = Signal(object)  # Dict[str, Any] или None
    error = Signal(str)

    def __init__(self, repository: IVibrationRepository, wtg_id: str, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.wtg_id = wtg_id

    def run(self):
        """Выполнить асинхронный запрос к БД."""
        try:
            logger.debug("Загрузка статистики для %s", self.wtg_id)
            result = asyncio.run(
                self.repository.get_turbine_statistics(self.wtg_id)
            )
            self.statistics_ready.emit(result)
        except Exception as e:
            logger.error("Ошибка загрузки статистики: %s", e, exc_info=True)
            self.error.emit(str(e))
