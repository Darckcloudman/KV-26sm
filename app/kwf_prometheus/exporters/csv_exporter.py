# -*- coding: utf-8 -*-
"""
Экспорт данных анализа в CSV.

Формат:
- Разделитель: точка с запятой (;)
- Кодировка: UTF-8 with BOM (для Excel в Windows)
- Первая строка — заголовки
"""

import csv
import io
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from ..dal.logger import get_logger

logger = get_logger("CSVExporter")


class CSVExporter:
    """Экспорт результатов анализа в CSV-файл."""

    def __init__(self, parser, sensor_id: int):
        """
        Инициализация экспортера.

        Args:
            parser: Парсер с данными (MultiSensorRD2Parser).
            sensor_id: ID датчика для экспорта.
        """
        self.parser = parser
        self.sensor_id = sensor_id
        self.data = parser.get_sensor_data(sensor_id) if parser else None

    def export(self, file_path: Path) -> bool:
        """
        Экспортировать данные в CSV.

        Args:
            file_path: Путь для сохранения файла.

        Returns:
            True если экспорт успешен.
        """
        if self.data is None:
            logger.error("Нет данных для экспорта (sensor_id=%d)", self.sensor_id)
            return False

        try:
            file_path = Path(file_path)
            logger.info("Экспорт CSV: %s", file_path)

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)

                # === Лист 1: Метаданные турбины ===
                writer.writerow(['=== МЕТАДАННЫЕ ТУРБИНЫ ==='])
                self._write_metadata(writer)
                writer.writerow([])

                # === Лист 2: Временные ряды ===
                writer.writerow(['=== ВРЕМЕННЫЕ РЯДЫ ==='])
                self._write_time_series(writer)
                writer.writerow([])

                # === Лист 3: Спектры ===
                writer.writerow(['=== СПЕКТРЫ ==='])
                self._write_spectrums(writer)
                writer.writerow([])

                # === Лист 4: Результаты анализа ===
                writer.writerow(['=== РЕЗУЛЬТАТЫ АНАЛИЗА (RMS, Зоны ISO 10816) ==='])
                self._write_analysis_results(writer)

            logger.info("CSV экспорт завершён: %s", file_path)
            return True

        except Exception as e:
            logger.error("Ошибка экспорта CSV: %s", e, exc_info=True)
            return False

    def _write_metadata(self, writer: csv.writer):
        """Записать метаданные турбины."""
        metrics = self.parser.get_turbine_metrics()
        writer.writerow(['Параметр', 'Значение', 'Единица'])
        writer.writerow(['Мощность', f"{metrics.get('power_kw', 0):.1f}", 'кВт'])
        writer.writerow(['Частота вращения', f"{metrics.get('generator_speed_rpm', 0):.1f}", 'об/мин'])
        writer.writerow(['Скорость ветра', f"{metrics.get('wind_speed_ms', 0):.1f}", 'м/с'])
        writer.writerow(['Накопленная выработка', f"{metrics.get('cumulative_power_kwh', 0):.1f}", 'кВт·ч'])

    def _write_time_series(self, writer: csv.writer):
        """Записать временные ряды."""
        writer.writerow(['Тип сигнала', 'Время (с)', 'Значение'])

        if self.data.get('acceleration') is not None and self.data.get('acceleration_time') is not None:
            for t, val in zip(self.data['acceleration_time'], self.data['acceleration']):
                writer.writerow(['НЧ (Ускорение)', f"{t:.6f}", f"{val:.6f}"])

        if self.data.get('velocity') is not None and self.data.get('velocity_time') is not None:
            for t, val in zip(self.data['velocity_time'], self.data['velocity']):
                writer.writerow(['ВЧ (Скорость)', f"{t:.6f}", f"{val:.6f}"])

        if self.data.get('high_freq') is not None and self.data.get('high_freq_time') is not None:
            for t, val in zip(self.data['high_freq_time'], self.data['high_freq']):
                writer.writerow(['ВЧ(ф) (ВЧ фильтр)', f"{t:.6f}", f"{val:.6f}"])

    def _write_spectrums(self, writer: csv.writer):
        """Записать спектры."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        writer.writerow(['Тип сигнала', 'Частота (Гц)', 'Амплитуда'])

        for signal_type, signal_key, fs_key in [
            ('НЧ (Ускорение)', 'acceleration', 'acceleration_fs'),
            ('ВЧ (Скорость)', 'velocity', 'velocity_fs'),
            ('ВЧ(ф) (ВЧ фильтр)', 'high_freq', 'high_freq_fs'),
        ]:
            signal = self.data.get(signal_key)
            fs = self.data.get(fs_key)
            if signal is not None and fs:
                import numpy as np
                freqs, amps = analyzer.calculate_spectrum(np.array(signal), fs)
                for f, a in zip(freqs, amps):
                    writer.writerow([signal_type, f"{f:.3f}", f"{a:.6f}"])

    def _write_analysis_results(self, writer: csv.writer):
        """Записать результаты анализа (RMS, зоны)."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        writer.writerow(['Тип сигнала', 'RMS', 'Единица', 'Зона ISO 10816'])

        if self.data.get('acceleration') is not None:
            rms = np.sqrt(np.mean(np.array(self.data['acceleration']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            writer.writerow(['НЧ (Ускорение)', f"{rms:.6f}", 'м/с²', zone])

        if self.data.get('velocity') is not None:
            rms = np.sqrt(np.mean(np.array(self.data['velocity']) ** 2))
            zone = analyzer.determine_zone_vel(rms)
            writer.writerow(['ВЧ (Скорость)', f"{rms:.6f}", 'мм/с', zone])

        if self.data.get('high_freq') is not None:
            rms = np.sqrt(np.mean(np.array(self.data['high_freq']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            writer.writerow(['ВЧ(ф) (ВЧ фильтр)', f"{rms:.6f}", 'м/с²', zone])
