# -*- coding: utf-8 -*-
"""
Воркер для асинхронного получения трендов RMS.
"""

import asyncio
from typing import Optional
from PySide6.QtCore import QThread, Signal

from ...dal.repositories.base import IVibrationRepository
from ...dal.logger import get_logger

logger = get_logger(__name__)


class TrendsWorker(QThread):
    """Воркер для загрузки тренда RMS."""

    trend_ready = Signal(object)  # List[Dict[str, Any]]
    error = Signal(str)

    def __init__(
        self,
        repository: IVibrationRepository,
        wtg_id: Optional[str] = None,
        sensor_id: int = 1,
        filter_type: str = "LOW",
        parent=None
    ):
        super().__init__(parent)
        self.repository = repository
        self.wtg_id = wtg_id
        self.sensor_id = sensor_id
        self.filter_type = filter_type

    def run(self):
        """Выполнить асинхронный запрос к БД."""
        try:
            logger.debug(
                "Загрузка тренда: wtg_id=%s, sensor=%d, filter=%s",
                self.wtg_id, self.sensor_id, self.filter_type
            )
            result = asyncio.run(
                self.repository.get_rms_trend(
                    self.wtg_id,
                    self.sensor_id,
                    self.filter_type
                )
            )
            self.trend_ready.emit(result)
        except Exception as e:
            logger.error("Ошибка загрузки тренда: %s", e, exc_info=True)
            self.error.emit(str(e))
