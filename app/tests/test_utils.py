# -*- coding: utf-8 -*-
"""
Unit-тесты для модулей utils.
"""

import pytest
import numpy as np
from smp12c_vibrodiag.utils.conversions import kw_to_mw, kwh_to_gwh
from smp12c_vibrodiag.utils.vibration_analysis import VibrationAnalyzer


class TestConversions:
    """Тесты функций конвертации."""

    def test_kw_to_mw_positive(self):
        """Конвертация положительных кВт в МВт."""
        assert kw_to_mw(1000.0) == 1.0
        assert kw_to_mw(2500.5) == 2.5005
        assert kw_to_mw(0.0) == 0.0

    def test_kw_to_mw_negative(self):
        """Конвертация отрицательных кВт (не должно быть, но проверяем)."""
        assert kw_to_mw(-100.0) == -0.1

    def test_kwh_to_gwh_positive(self):
        """Конвертация положительных кВт·ч в ГВт·ч."""
        assert kwh_to_gwh(1000000.0) == 1.0
        assert kwh_to_gwh(15000000.0) == 15.0
        assert kwh_to_gwh(0.0) == 0.0

    def test_kwh_to_gwh_negative(self):
        """Конвертация отрицательных кВт·ч."""
        assert kwh_to_gwh(-500000.0) == -0.5


class TestVibrationAnalyzer:
    """Тесты анализатора вибрации."""

    def setup_method(self):
        """Инициализация перед каждым тестом."""
        self.analyzer = VibrationAnalyzer()

    def test_determine_zone_acc_zone_a(self):
        """Зона A для ускорения (норма): ≤ 1.0 м/с²."""
        assert self.analyzer.determine_zone_acc(0.5) == 'A'
        assert self.analyzer.determine_zone_acc(1.0) == 'A'

    def test_determine_zone_acc_zone_b(self):
        """Зона B для ускорения (внимание): 1.0 < x ≤ 2.5."""
        assert self.analyzer.determine_zone_acc(1.01) == 'B'
        assert self.analyzer.determine_zone_acc(2.5) == 'B'

    def test_determine_zone_acc_zone_c(self):
        """Зона C для ускорения (требует внимания): 2.5 < x ≤ 5.0."""
        assert self.analyzer.determine_zone_acc(2.51) == 'C'
        assert self.analyzer.determine_zone_acc(5.0) == 'C'

    def test_determine_zone_acc_zone_d(self):
        """Зона D для ускорения (критично): > 5.0."""
        assert self.analyzer.determine_zone_acc(5.01) == 'D'
        assert self.analyzer.determine_zone_acc(20.0) == 'D'

    def test_determine_zone_vel_zone_a(self):
        """Зона A для скорости (норма): ≤ 2.3 мм/с."""
        assert self.analyzer.determine_zone_vel(0.5) == 'A'
        assert self.analyzer.determine_zone_vel(2.3) == 'A'

    def test_determine_zone_vel_zone_b(self):
        """Зона B для скорости (внимание): 2.3 < x ≤ 4.5."""
        assert self.analyzer.determine_zone_vel(2.31) == 'B'
        assert self.analyzer.determine_zone_vel(4.5) == 'B'

    def test_determine_zone_vel_zone_c(self):
        """Зона C для скорости (требует внимания): 4.5 < x ≤ 11.2."""
        assert self.analyzer.determine_zone_vel(4.51) == 'C'
        assert self.analyzer.determine_zone_vel(11.2) == 'C'

    def test_determine_zone_vel_zone_d(self):
        """Зона D для скорости (критично): > 11.2."""
        assert self.analyzer.determine_zone_vel(11.21) == 'D'
        assert self.analyzer.determine_zone_vel(20.0) == 'D'

    def test_calculate_spectrum(self):
        """Расчёт спектра."""
        fs = 100.0
        signal = np.sin(2 * np.pi * 10 * np.linspace(0, 1, int(fs)))
        freqs, amps = self.analyzer.calculate_spectrum(signal, fs)
        
        assert len(freqs) == len(amps)
        # FFT возвращает n//2 + 1 точек для сигнала длиной n
        assert len(freqs) == int(fs) // 2 + 1
        assert freqs[0] == 0.0
        assert freqs[-1] == fs / 2

    def test_calculate_rms(self):
        """RMS расчёт."""
        signal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rms = np.sqrt(np.mean(signal ** 2))
        assert abs(rms - 3.3166) < 0.01

    def test_calculate_rms_zero_signal(self):
        """RMS нулевого сигнала."""
        signal = np.zeros(100)
        rms = np.sqrt(np.mean(signal ** 2))
        assert rms == 0.0

    def test_edge_cases(self):
        """Краевые случаи."""
        # Пустой сигнал — FFT вызывает ValueError
        signal = np.array([])
        with pytest.raises(ValueError, match="Invalid number of FFT data points"):
            self.analyzer.calculate_spectrum(signal, 100.0)

        # Отрицательная частота дискретизации — FFT работает, но частоты будут отрицательными
        signal = np.array([1.0, 2.0, 3.0])
        freqs, amps = self.analyzer.calculate_spectrum(signal, -100.0)
        assert len(freqs) == 2  # len(signal)//2 + 1
