# -*- coding: utf-8 -*-
"""
Потоки для экспорта данных без блокировки GUI.
"""

from pathlib import Path
from typing import Union
from PySide6.QtCore import QThread, Signal

from ..dal.logger import get_logger
from ..exporters.csv_exporter import CSVExporter
from ..exporters.excel_exporter import ExcelExporter

logger = get_logger("ExportThread")


class ExportWorker(QThread):
    """Поток для выполнения экспорта данных."""

    progress = Signal(int, str)  # процент, сообщение
    finished = Signal(bool, str)  # успех, сообщение

    def __init__(self, export_type: str, parser, sensor_id: int, file_path: Union[str, Path], parent=None):
        """
        Инициализация потока экспорта.

        Args:
            export_type: 'csv' или 'excel'.
            parser: Парсер с данными.
            sensor_id: ID датчика.
            file_path: Путь для сохранения.
        """
        super().__init__(parent)
        self.export_type = export_type
        self.parser = parser
        self.sensor_id = sensor_id
        self.file_path = Path(file_path)

    def run(self):
        """Выполнить экспорт."""
        try:
            logger.info("Начало экспорта %s: %s", self.export_type.upper(), self.file_path)
            self.progress.emit(10, "Подготовка данных...")

            if self.export_type == 'csv':
                exporter = CSVExporter(self.parser, self.sensor_id)
            elif self.export_type == 'excel':
                exporter = ExcelExporter(self.parser, self.sensor_id)
            else:
                self.finished.emit(False, f"Неизвестный тип экспорта: {self.export_type}")
                return

            self.progress.emit(50, "Запись файла...")
            success = exporter.export(self.file_path)

            if success:
                self.progress.emit(100, "Готово!")
                self.finished.emit(True, f"Экспорт завершён: {self.file_path}")
                logger.info("Экспорт %s успешен", self.export_type.upper())
            else:
                self.finished.emit(False, "Ошибка при экспорте данных")

        except Exception as e:
            logger.error("Ошибка в потоке экспорта: %s", e, exc_info=True)
            self.finished.emit(False, f"Ошибка экспорта: {str(e)}")
