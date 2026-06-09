# -*- coding: utf-8 -*-
"""
Модуль логирования для DAL (Data Access Layer).

Настраивает логирование в файл и консоль для всех операций DAL.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


# Формат логов: 2025-05-20 14:30:15 - DAL.PostgresRepository - INFO - Сообщение
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Максимальный размер файла лога: 5 МБ, хранить 3 резервных копии
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def setup_logging(
    level: int = logging.INFO,
    log_file: Path = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    Настроить логирование для DAL.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
        log_file: Путь к файлу логов. По умолчанию app.log рядом с приложением.
        enable_console: Дублировать логи в консоль.

    Returns:
        Корневой логгер DAL.
    """
    if log_file is None:
        # app.log в корне проекта (рядом с main.py)
        log_file = Path(__file__).resolve().parent.parent.parent / "app.log"

    # Создаём директорию для лога если нужно
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Корневой логгер DAL
    dal_logger = logging.getLogger("DAL")
    dal_logger.setLevel(level)

    # Очищаем старые обработчики (для повторных вызовов)
    if dal_logger.handlers:
        dal_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Файловый обработчик (rotating)
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    dal_logger.addHandler(file_handler)

    # Консольный обработчик
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        dal_logger.addHandler(console_handler)

    return dal_logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер для конкретного модуля DAL.

    Args:
        name: Имя модуля (например, 'PostgresRepository', 'DatabaseManager').

    Returns:
        Логгер с именем DAL.<name>.
    """
    return logging.getLogger(f"DAL.{name}")
