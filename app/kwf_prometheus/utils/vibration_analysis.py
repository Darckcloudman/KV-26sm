"""
Модуль анализа вибрации согласно ISO 10816-21:2015 и ГОСТ 10816-21-2021.

Зоны оценки состояния:
- Зона A: Узлы нового ветрогенератора, только что введённого в эксплуатацию.
          Работают в условиях постоянных нагрузок и низкой турбулентности.
- Зона B: Узлы, пригодные для дальнейшего функционирования без ограничения сроков.
- Зона C: Узлы, непригодные для длительной непрерывной эксплуатации.
          Требуется выяснение причины повышенной вибрации.
- Зона D: Узлы с критическим уровнем вибрации. Требуется немедленная остановка.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import numpy as np
from scipy.signal import butter, filtfilt


class VibrationZone(Enum):
    """Зона вибрации согласно ISO 10816-21 / ГОСТ 10816-21."""
    A = "A"      # Отлично
    B = "B"      # Хорошо
    C = "C"      # Удовлетворительно (требуется внимание)
    D = "D"      # Критически (остановка)


@dataclass
class VibrationResult:
    """Результат анализа вибрации."""
    value: float          # Значение вибрации
    unit: str             # Единица измерения
    zone: VibrationZone   # Зона оценки
    description: str      # Описание зоны


# Пороговые значения для виброускорения (м/с²) в диапазоне 0.1–10 Гц
# Значения ориентированы на крупные ветрогенераторы (>300 кВт)
ACCELERATION_THRESHOLDS_MS2 = {
    VibrationZone.A: 1.0,   # ≤ 1.0 м/с² — зона A
    VibrationZone.B: 2.5,   # ≤ 2.5 м/с² — зона B
    VibrationZone.C: 5.0,   # ≤ 5.0 м/с² — зона C
    # > 5.0 м/с² — зона D
}

# Пороговые значения для виброскорости (мм/с) в диапазоне 10–1000 Гц
# Значения ориентированы на крупные ветрогенераторы (>300 кВт)
VELOCITY_THRESHOLDS_MM_S = {
    VibrationZone.A: 2.3,   # ≤ 2.3 мм/с — зона A
    VibrationZone.B: 4.5,   # ≤ 4.5 мм/с — зона B
    VibrationZone.C: 11.2,  # ≤ 11.2 мм/с — зона C
    # > 11.2 мм/с — зона D
}


ZONE_DESCRIPTIONS = {
    VibrationZone.A: (
        "Зона A: Узел нового ветрогенератора, только что введённого в эксплуатацию. "
        "Работает в условиях постоянных нагрузок и низкой турбулентности."
    ),
    VibrationZone.B: (
        "Зона B: Узел пригоден для дальнейшего функционирования без ограничения сроков."
    ),
    VibrationZone.C: (
        "Зона C: Узел непригоден для длительной непрерывной эксплуатации. "
        "Требуется выяснение причины повышенной вибрации."
    ),
    VibrationZone.D: (
        "Зона D: Критический уровень вибрации. Требуется немедленная остановка!"
    ),
}


def evaluate_acceleration_zone(value_ms2: float) -> VibrationResult:
    """
    Оценить зону вибрации по виброускорению (м/с²).

    Диапазон частот: 0.1–10 Гц (НЧ).

    Args:
        value_ms2: Значение виброускорения в м/с².

    Returns:
        VibrationResult с оценкой зоны.
    """
    if value_ms2 <= ACCELERATION_THRESHOLDS_MS2[VibrationZone.A]:
        zone = VibrationZone.A
    elif value_ms2 <= ACCELERATION_THRESHOLDS_MS2[VibrationZone.B]:
        zone = VibrationZone.B
    elif value_ms2 <= ACCELERATION_THRESHOLDS_MS2[VibrationZone.C]:
        zone = VibrationZone.C
    else:
        zone = VibrationZone.D

    return VibrationResult(
        value=round(value_ms2, 3),
        unit="м/с²",
        zone=zone,
        description=ZONE_DESCRIPTIONS[zone]
    )


def evaluate_velocity_zone(value_mm_s: float) -> VibrationResult:
    """
    Оценить зону вибрации по виброскорости (мм/с).

    Диапазон частот: 10–1000 Гц (ВЧ).

    Args:
        value_mm_s: Значение виброскорости в мм/с.

    Returns:
        VibrationResult с оценкой зоны.
    """
    if value_mm_s <= VELOCITY_THRESHOLDS_MM_S[VibrationZone.A]:
        zone = VibrationZone.A
    elif value_mm_s <= VELOCITY_THRESHOLDS_MM_S[VibrationZone.B]:
        zone = VibrationZone.B
    elif value_mm_s <= VELOCITY_THRESHOLDS_MM_S[VibrationZone.C]:
        zone = VibrationZone.C
    else:
        zone = VibrationZone.D

    return VibrationResult(
        value=round(value_mm_s, 2),
        unit="мм/с",
        zone=zone,
        description=ZONE_DESCRIPTIONS[zone]
    )


def get_zone_color(zone: VibrationZone) -> str:
    """
    Получить цвет для отображения зоны в HEX формате.

    Args:
        zone: Зона вибрации.

    Returns:
        HEX-цвет.
    """
    colors = {
        VibrationZone.A: "#00C853",  # Зелёный
        VibrationZone.B: "#FFD600",  # Жёлтый
        VibrationZone.C: "#FFAB00",  # Оранжевый
        VibrationZone.D: "#D50000",  # Красный
    }
    return colors.get(zone, "#FFFFFF")


def calculate_rms(data: np.ndarray) -> float:
    """Вычислить среднеквадратичное значение (RMS)."""
    return float(np.sqrt(np.mean(np.square(data))))


def apply_bandpass_filter(
    data: np.ndarray,
    low_freq: float,
    high_freq: float,
    sample_rate: float
) -> np.ndarray:
    """
    Применить полосовой фильтр к данным.

    Args:
        data: Входные данные.
        low_freq: Нижняя граница частоты (Гц).
        high_freq: Верхняя граница частоты (Гц).
        sample_rate: Частота дискретизации (Гц).

    Returns:
        Отфильтрованные данные.
    """
    nyquist = sample_rate / 2
    low = low_freq / nyquist
    high = high_freq / nyquist

    # Ограничиваем границы частот
    low = max(0.01, min(low, 0.99))
    high = max(low + 0.01, min(high, 0.99))

    b, a = butter(4, [low, high], btype='band')
    return filtfilt(b, a, data)


def compute_spectrum(data: np.ndarray, sample_rate: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Вычислить спектр (FFT) данных.

    Args:
        data: Входные данные.
        sample_rate: Частота дискретизации (Гц).

    Returns:
        Кортеж (частоты, амплитуды).
    """
    n = len(data)
    fft_result = np.fft.rfft(data)
    frequencies = np.fft.rfftfreq(n, 1 / sample_rate)
    amplitudes = np.abs(fft_result) / n

    return frequencies, amplitudes


class VibrationAnalyzer:
    """Класс-обёртка для анализа вибрации (совместимость с GUI)."""

    @staticmethod
    def calculate_spectrum(values: np.ndarray, sampling_freq: float) -> Tuple[np.ndarray, np.ndarray]:
        """Вычислить спектр через FFT."""
        return compute_spectrum(values, sampling_freq)

    @staticmethod
    def determine_zone_acc(rms_value: float) -> str:
        """Определить зону по ускорению (м/с²)."""
        result = evaluate_acceleration_zone(rms_value)
        return result.zone.value

    @staticmethod
    def determine_zone_vel(rms_value: float) -> str:
        """Определить зону по скорости (мм/с)."""
        result = evaluate_velocity_zone(rms_value)
        return result.zone.value
