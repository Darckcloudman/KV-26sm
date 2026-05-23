# -*- coding: utf-8 -*-
"""
Фикстуры для pytest.
"""

import pytest
import numpy as np
from pathlib import Path


@pytest.fixture
def sample_vibration_data():
    """Тестовые данные вибрации."""
    return {
        'acceleration': np.random.randn(1000) * 0.5,
        'acceleration_time': np.linspace(0, 10, 1000),
        'acceleration_fs': 100.0,
        'velocity': np.random.randn(1000) * 2.0,
        'velocity_time': np.linspace(0, 10, 1000),
        'velocity_fs': 100.0,
        'high_freq': np.random.randn(1000) * 0.3,
        'high_freq_time': np.linspace(0, 10, 1000),
        'high_freq_fs': 100.0,
    }


@pytest.fixture
def sample_turbine_metrics():
    """Тестовые метрики турбины."""
    return {
        'power_kw': 2500.5,
        'generator_speed_rpm': 1500.0,
        'wind_speed_ms': 12.5,
        'cumulative_power_kwh': 15000000.0,
    }


@pytest.fixture
def temp_dir(tmp_path):
    """Временная директория для тестов."""
    return tmp_path
