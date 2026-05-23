# -*- coding: utf-8 -*-
"""
Воркеры для асинхронной загрузки данных из БД.
"""

from .statistics_worker import StatisticsWorker
from .trends_worker import TrendsWorker

__all__ = ['StatisticsWorker', 'TrendsWorker']
