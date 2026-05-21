# -*- coding: utf-8 -*-
"""
Unit-тесты для модулей отчётности.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
import numpy as np

from smp12c_vibrodiag.reports.pdf_generator import PDFReportGenerator


class MockParser:
    """Фейковый парсер для тестов PDF."""

    def __init__(self):
        self._metrics = {
            'power_kw': 2500.5,
            'generator_speed_rpm': 1500.0,
            'wind_speed_ms': 12.5,
            'cumulative_power_kwh': 15000000.0,
        }
        self._sensor_data = {}
        for sid in range(1, 9):
            self._sensor_data[sid] = {
                'acceleration': np.random.randn(100) * 0.5,
                'acceleration_time': np.linspace(0, 10, 100),
                'acceleration_fs': 100.0,
                'velocity': np.random.randn(100) * 2.0,
                'velocity_time': np.linspace(0, 10, 100),
                'velocity_fs': 100.0,
                'high_freq': np.random.randn(100) * 0.3,
                'high_freq_time': np.linspace(0, 10, 100),
                'high_freq_fs': 100.0,
            }

    def get_turbine_metrics(self):
        return self._metrics

    def get_sensor_data(self, sensor_id):
        return self._sensor_data.get(sensor_id)

    def get_available_sensors(self):
        return list(self._sensor_data.keys())


class TestPDFReportGenerator:
    """Тесты генератора PDF-отчётов."""

    def setup_method(self):
        """Инициализация перед каждым тестом."""
        self.parser = MockParser()
        self.generator = PDFReportGenerator(self.parser, sensor_id=1)

    def test_generator_creation(self):
        """Создание генератора."""
        assert self.generator.parser is not None
        assert self.generator.sensor_id == 1
        assert self.generator.data is not None
        assert self.generator.metrics is not None

    def test_generate_creates_file(self, temp_dir):
        """Генерация создаёт PDF файл."""
        file_path = temp_dir / "test_report.pdf"
        success = self.generator.generate(file_path)
        
        assert success is True
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    def test_generate_content(self, temp_dir):
        """Проверка содержания PDF."""
        file_path = temp_dir / "test_report.pdf"
        self.generator.generate(file_path)
        
        # Проверяем что файл валидный PDF (по заголовку)
        content = file_path.read_bytes()
        assert content.startswith(b'%PDF-')

    def test_generate_with_charts(self, temp_dir):
        """Генерация с графиками."""
        # Создаём фейковые изображения
        chart_images = {}
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots()
            ax.plot([1, 2, 3], [1, 4, 9])
            temp_path = temp_dir / "test_chart.png"
            fig.savefig(temp_path)
            plt.close(fig)
            
            chart_images['Тестовый график'] = str(temp_path)
        except ImportError:
            pytest.skip("matplotlib не установлен")
        
        file_path = temp_dir / "report_with_charts.pdf"
        success = self.generator.generate(file_path, chart_images)
        
        assert success is True
        assert file_path.exists()

    def test_generate_no_data(self, temp_dir):
        """Генерация без данных."""
        empty_parser = Mock()
        empty_parser.get_sensor_data = Mock(return_value=None)
        empty_parser.get_turbine_metrics = Mock(return_value={})
        
        generator = PDFReportGenerator(empty_parser, sensor_id=1)
        file_path = temp_dir / "empty.pdf"
        success = generator.generate(file_path)
        
        # Должен создать пустой отчёт или вернуть False
        assert success in [True, False]
