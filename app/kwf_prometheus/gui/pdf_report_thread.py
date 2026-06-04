# -*- coding: utf-8 -*-
"""
Поток для генерации PDF-отчётов без блокировки GUI.
"""

import tempfile
from pathlib import Path
from typing import Union
from PySide6.QtCore import QThread, Signal

from ..dal.logger import get_logger
from ..reports.pdf_generator import PDFReportGenerator

logger = get_logger("PDFReportThread")


class PDFReportWorker(QThread):
    """Поток для генерации PDF-отчёта."""

    progress = Signal(int, str)  # процент, сообщение
    finished = Signal(bool, str)  # успех, сообщение

    def __init__(self, parser, sensor_id: int, file_path: Union[str, Path], parent=None):
        """
        Инициализация потока.

        Args:
            parser: Парсер с данными.
            sensor_id: ID датчика для отчёта.
            file_path: Путь для сохранения PDF.
        """
        super().__init__(parent)
        self.parser = parser
        self.sensor_id = sensor_id
        self.file_path = Path(file_path)
        self._temp_images = []

    def run(self):
        """Выполнить генерацию PDF."""
        try:
            logger.info("Начало генерации PDF: %s", self.file_path)
            self.progress.emit(10, "Подготовка данных...")

            # Создаём временные изображения графиков
            chart_images = self._generate_chart_images()

            self.progress.emit(60, "Формирование PDF...")
            generator = PDFReportGenerator(self.parser, self.sensor_id)
            success = generator.generate(self.file_path, chart_images)

            # Удаляем временные файлы
            self._cleanup_temp_images()

            if success:
                self.progress.emit(100, "Готово!")
                self.finished.emit(True, f"PDF-отчёт создан: {self.file_path}")
                logger.info("PDF-отчёт успешно создан")
            else:
                self.finished.emit(False, "Ошибка при создании PDF-отчёта")

        except Exception as e:
            self._cleanup_temp_images()
            logger.error("Ошибка генерации PDF: %s", e, exc_info=True)
            self.finished.emit(False, f"Ошибка: {str(e)}")

    def _generate_chart_images(self) -> dict:
        """Сгенерировать временные PNG-изображения графиков с поддержкой кириллицы."""
        import numpy as np
        from ..utils.vibration_analysis import VibrationAnalyzer

        # === НАСТРОЙКА КИРИЛЛИЦЫ ДЛЯ MATPLOTLIB ===
        import matplotlib
        matplotlib.use('Agg')
        
        # Настройка шрифтов для поддержки кириллицы
        matplotlib.rcParams['font.family'] = 'DejaVu Sans'
        matplotlib.rcParams['axes.unicode_minus'] = False  # Для корректного отображения минуса
        
        import matplotlib.pyplot as plt

        chart_images = {}
        data = self.parser.get_sensor_data(self.sensor_id)
        if data is None:
            return chart_images

        analyzer = VibrationAnalyzer()

        # Временной ряд (НЧ)
        if data.get('acceleration') is not None and data.get('acceleration_time') is not None:
            self.progress.emit(20, "Создание графика временного ряда...")
            try:
                fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
                ax.plot(data['acceleration_time'], data['acceleration'], color='black', linewidth=0.8)
                ax.set_xlabel('Время, с', fontsize=10)
                ax.set_ylabel('Ускорение, м/с²', fontsize=10)
                ax.set_title(f'Датчик {self.sensor_id} — НЧ (0.1–10 Гц)', fontsize=11)
                ax.grid(True, alpha=0.3)
                ax.set_facecolor('white')
                fig.patch.set_facecolor('white')

                temp_path = tempfile.mktemp(suffix='.png')
                fig.savefig(temp_path, bbox_inches='tight', dpi=100, encoding='utf-8')
                plt.close(fig)
                chart_images['Временной ряд (НЧ)'] = temp_path
                self._temp_images.append(temp_path)
            except Exception as e:
                logger.warning("Не удалось создать график временного ряда: %s", e)

        # Спектр (НЧ)
        if data.get('acceleration') is not None and data.get('acceleration_fs'):
            self.progress.emit(35, "Создание спектра...")
            try:
                acc = np.array(data['acceleration'])
                fs = data['acceleration_fs']
                freqs, amps = analyzer.calculate_spectrum(acc, fs)
                mask = freqs <= 30

                fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
                ax.plot(freqs[mask], amps[mask], color='black', linewidth=0.8)
                ax.set_xlabel('Частота, Гц', fontsize=10)
                ax.set_ylabel('Амплитуда, м/с²', fontsize=10)
                ax.set_title(f'Датчик {self.sensor_id} — Спектр НЧ', fontsize=11)
                ax.grid(True, alpha=0.3)
                ax.set_facecolor('white')
                fig.patch.set_facecolor('white')

                temp_path = tempfile.mktemp(suffix='.png')
                fig.savefig(temp_path, bbox_inches='tight', dpi=100, encoding='utf-8')
                plt.close(fig)
                chart_images['Спектр (НЧ)'] = temp_path
                self._temp_images.append(temp_path)
            except Exception as e:
                logger.warning("Не удалось создать спектр: %s", e)

        # Спектр (ВЧ)
        if data.get('velocity') is not None and data.get('velocity_fs'):
            self.progress.emit(45, "Создание спектра ВЧ...")
            try:
                vel = np.array(data['velocity'])
                fs = data['velocity_fs']
                freqs, amps = analyzer.calculate_spectrum(vel, fs)
                mask = freqs <= 1200

                fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
                ax.plot(freqs[mask], amps[mask], color='black', linewidth=0.8)
                ax.set_xlabel('Частота, Гц', fontsize=10)
                ax.set_ylabel('Амплитуда, мм/с', fontsize=10)
                ax.set_title(f'Датчик {self.sensor_id} — Спектр ВЧ', fontsize=11)
                ax.grid(True, alpha=0.3)
                ax.set_facecolor('white')
                fig.patch.set_facecolor('white')

                temp_path = tempfile.mktemp(suffix='.png')
                fig.savefig(temp_path, bbox_inches='tight', dpi=100, encoding='utf-8')
                plt.close(fig)
                chart_images['Спектр (ВЧ)'] = temp_path
                self._temp_images.append(temp_path)
            except Exception as e:
                logger.warning("Не удалось создать спектр ВЧ: %s", e)

        return chart_images

    def _cleanup_temp_images(self):
        """Удалить временные изображения."""
        for img_path in self._temp_images:
            try:
                Path(img_path).unlink(missing_ok=True)
            except Exception:
                pass
        self._temp_images.clear()
