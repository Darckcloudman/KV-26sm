# -*- coding: utf-8 -*-
"""
Парсер файлов .rd2/.rw2 SMP12C

Этот модуль предоставляет класс для чтения и анализа файлов вибродиагностики
от системы SMP12C (Siemens Gamesa Renewable Energy).

Формат файла: текстовый CSV-подобный
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import os
import re
import zipfile
from pathlib import Path

from ..utils.conversions import kw_to_mw, kwh_to_gwh


def extract_number(value: str) -> float:
    """Извлечь число из строки с единицами (например, '25600 Hz' -> 25600.0)"""
    match = re.match(r'([\d.]+)', str(value).strip())
    return float(match.group(1)) if match else 0.0


def _parse_key_value_line(metadata: dict, line: str, mapping: dict):
    """Универсальный парсер строки формата Key, Value, Unit, Key, Value..."""
    parts = [p.strip() for p in line.split(',')]
    for i, part in enumerate(parts):
        if part in mapping and i + 1 < len(parts):
            metadata[mapping[part]] = parts[i + 1]


class RD2Parser:
    """Парсер файлов .rd2/.rw2 SMP12C"""

    def __init__(self, filepath: str):
        """
        Инициализация парсера

        Args:
            filepath: путь к файлу .rd2 или .rw2
        """
        self.filepath = filepath
        self.metadata: Dict = {}
        self.data: Optional[np.ndarray] = None
        self.timestamps: Optional[np.ndarray] = None

    def parse(self) -> Dict:
        """
        Основная функция парсинга
        Возвращает словарь с метаданными и данными

        Returns:
            словарь с ключами:
            - metadata: dict с метаданными
            - timestamps: numpy array временных меток
            - values: numpy array значений виброскорости
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Файл не найден: {self.filepath}")

        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Парсинг заголовка (первые 5 строк)
        self._parse_header(lines[:5])

        # Парсинг данных (остальные строки)
        self._parse_data(lines[5:])

        return {
            'metadata': self.metadata,
            'timestamps': self.timestamps,
            'values': self.data
        }

    def _parse_header(self, header_lines: list):
        """Парсинг заголовка файла с поддержкой двух форматов."""

        # Строка 1: Основная информация (формат одинаковый)
        line1 = header_lines[0].strip().split(', ')
        self.metadata['record_number'] = line1[0]
        self.metadata['sensor_serial'] = line1[0]  # v1.4: серийный номер датчика (первое поле)
        self.metadata['record_datetime'] = line1[1]
        self.metadata['turbine_id'] = line1[2]
        self.metadata['wtg_id'] = line1[3]
        self.metadata['sensor_name'] = line1[4]

        # Строка 2: Параметры дискретизации
        line2_mapping = {
            'Sampling Time': 'sampling_time',
            'Sampling Frequency': 'sampling_frequency',
            'Samples': 'samples',
            'Duration': 'record_length',
        }
        _parse_key_value_line(self.metadata, header_lines[1], line2_mapping)
        if 'sampling_time' not in self.metadata:
            # Fallback: старый формат без названий полей
            line2 = header_lines[1].strip().split(', ')
            self.metadata['sampling_time'] = extract_number(line2[0])
            self.metadata['sampling_frequency'] = extract_number(line2[1])
            self.metadata['samples'] = int(extract_number(line2[2]))
            self.metadata['record_length'] = extract_number(line2[4]) if len(line2) > 4 else 0.0
        else:
            self.metadata['sampling_time'] = float(extract_number(self.metadata['sampling_time']))
            self.metadata['sampling_frequency'] = float(extract_number(self.metadata['sampling_frequency']))
            self.metadata['samples'] = int(extract_number(self.metadata['samples']))
            self.metadata['record_length'] = float(extract_number(self.metadata['record_length']))

        # Строка 3: Параметры турбины
        line3_mapping = {
            'Generator Speed': 'generator_speed',
            'Active Power': 'active_power',
            'Wind Speed': 'wind_speed',
            'Cumulative Power': 'cumulative_power',
        }
        _parse_key_value_line(self.metadata, header_lines[2], line3_mapping)
        if 'generator_speed' not in self.metadata:
            # Fallback: старый формат без названий полей
            line3 = header_lines[2].strip().split(', ')
            self.metadata['generator_speed'] = int(extract_number(line3[0]))
            self.metadata['active_power'] = int(extract_number(line3[1]))
            self.metadata['wind_speed'] = extract_number(line3[2])
            self.metadata['cumulative_power'] = extract_number(line3[4]) if len(line3) > 4 else 0.0
        else:
            self.metadata['generator_speed'] = int(extract_number(self.metadata['generator_speed']))
            self.metadata['active_power'] = int(extract_number(self.metadata['active_power']))
            self.metadata['wind_speed'] = extract_number(self.metadata['wind_speed'])
            self.metadata['cumulative_power'] = extract_number(self.metadata['cumulative_power'])

        # Строка 4: Информация об устройстве
        line4_mapping = {
            'Device': 'device',
            'Serial Number': 'device_serial',
            'MAC': 'mac_address',
            'IP': 'ip_address',
            'FW version': 'firmware_version',
        }
        _parse_key_value_line(self.metadata, header_lines[3], line4_mapping)
        if 'device' not in self.metadata:
            # Fallback: старый формат без названий полей
            line4 = header_lines[3].strip().split(', ')
            self.metadata['device'] = line4[0].replace('Device: ', '')
            if len(line4) > 1:
                self.metadata['device_serial'] = line4[1].replace('SN: ', '')
            if len(line4) > 2:
                self.metadata['mac_address'] = line4[2].replace('MAC: ', '')
            if len(line4) > 3:
                self.metadata['ip_address'] = line4[3].replace('IP: ', '')
            if len(line4) > 4:
                self.metadata['firmware_version'] = line4[4].replace('FW: ', '')

        # Строка 5: Конфигурация
        line5_mapping = {
            'Number of Configuration': 'config_number',
            'Configuration Table Version': 'config_table_version',
            'Layout Version': 'layout_version',
            'Exception Applied': 'exception_applied',
            'PLC IP Address': 'plc_ip',
        }
        _parse_key_value_line(self.metadata, header_lines[4], line5_mapping)
        if 'config_number' not in self.metadata:
            # Fallback: старый формат без названий полей
            line5 = header_lines[4].strip().split(', ')
            self.metadata['config_number'] = int(extract_number(line5[0].replace('Config: ', '')))
            if len(line5) > 1:
                self.metadata['config_table_version'] = int(extract_number(line5[1].replace('Table: ', '')))
            if len(line5) > 2:
                self.metadata['layout_version'] = int(extract_number(line5[2].replace('Layout: ', '')))
            if len(line5) > 3:
                self.metadata['exception_applied'] = int(extract_number(line5[3].replace('Exception: ', '')))
            if len(line5) > 4:
                self.metadata['plc_ip'] = line5[4].replace('PLC: ', '')
        else:
            self.metadata['config_number'] = int(extract_number(self.metadata['config_number']))
            self.metadata['config_table_version'] = int(extract_number(self.metadata['config_table_version']))
            self.metadata['layout_version'] = int(extract_number(self.metadata['layout_version']))
            self.metadata['exception_applied'] = int(extract_number(self.metadata['exception_applied']))

    def _parse_data(self, data_lines: list):
        """Парсинг данных вибрации"""

        timestamps = []
        values = []

        for line in data_lines:
            if not line.strip():
                continue

            # Удаляем trailing запятую и разделяем
            parts = line.strip().rstrip(',').split(', ')
            if len(parts) >= 3:
                try:
                    # parts[0] = индекс, parts[1] = время, parts[2] = значение
                    timestamps.append(float(parts[1]))
                    values.append(float(parts[2]))
                except (ValueError, IndexError) as e:
                    # Пропускаем некорректные строки
                    continue

        self.timestamps = np.array(timestamps)
        self.data = np.array(values)


class VibrationAnalyzer:
    """Анализатор вибрационных данных"""

    @staticmethod
    def calculate_rms(values: np.ndarray, window_size: int = 1024) -> Dict:
        """
        Вычисление скользящего СКЗ

        Args:
            values: массив значений виброскорости
            window_size: размер окна для расчета СКЗ

        Returns:
            словарь с результатами:
            - rms_values: список словарей с временными метками и СКЗ
            - total_rms: общее СКЗ для всего сигнала
            - peak: пиковое значение
            - peak_to_peak: размах
        """
        rms_values = []
        step = window_size // 2  # Перекрытие 50%

        for i in range(0, len(values) - window_size, step):
            window = values[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            rms_values.append({
                'index': i,
                'rms': rms
            })

        # Общее СКЗ для всего сигнала
        total_rms = np.sqrt(np.mean(values ** 2))

        return {
            'rms_values': rms_values,
            'total_rms': total_rms,
            'peak': np.max(np.abs(values)),
            'peak_to_peak': np.max(values) - np.min(values)
        }

    @staticmethod
    def calculate_spectrum(values: np.ndarray, sampling_freq: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Вычисление спектра через FFT

        Args:
            values: массив значений виброскорости
            sampling_freq: частота дискретизации (Гц)

        Returns:
            (frequencies, amplitudes) - частоты и амплитуды
        """
        n = len(values)

        # Вычисление FFT
        fft_result = np.fft.rfft(values)

        # Частоты
        frequencies = np.fft.rfftfreq(n, d=1/sampling_freq)

        # Амплитуды (абсолютные значения)
        amplitudes = np.abs(fft_result) * 2 / n

        # Убираем DC компоненту (0 Гц)
        frequencies = frequencies[1:]
        amplitudes = amplitudes[1:]

        return frequencies, amplitudes

    @staticmethod
    def determine_zone(rms_value: float) -> str:
        """
        Определение зоны состояния по ISO 10816

        Зоны для виброскорости (мм/с):
        - Zone A: < 2.3 мм/с (Хорошо)
        - Zone B: 2.3 - 4.5 мм/с (Удовлетворительно)
        - Zone C: 4.5 - 7.8 мм/с (Неудовлетворительно)
        - Zone D: > 7.8 мм/с (Критично)

        Args:
            rms_value: значение СКЗ виброскорости

        Returns:
            'A', 'B', 'C' или 'D'
        """
        if rms_value < 2.3:
            return 'A'
        elif rms_value < 4.5:
            return 'B'
        elif rms_value < 7.8:
            return 'C'
        else:
            return 'D'

    @staticmethod
    def find_spectrum_peaks(frequencies: np.ndarray, amplitudes: np.ndarray,
                           top_n: int = 10) -> List[Dict]:
        """
        Поиск пиков в спектре

        Args:
            frequencies: массив частот
            amplitudes: массив амплитуд
            top_n: количество пиков для возврата

        Returns:
            список пиков с частотой и амплитудой
        """
        # Сортируем по амплитуде
        indices = np.argsort(amplitudes)[::-1][:top_n]

        peaks = []
        for idx in indices:
            peaks.append({
                'frequency': frequencies[idx],
                'amplitude': amplitudes[idx]
            })

        return peaks


def process_rd2_file(filepath: str) -> Dict:
    """
    Полный алгоритм обработки файла .rd2

    Args:
        filepath: путь к файлу

    Returns:
        словарь со всеми результатами:
        - metadata: метаданные файла
        - rms: результаты расчета СКЗ
        - spectrum: спектр (частоты и амплитуды)
        - zone: зона состояния
        - peaks: пики в спектре
        - raw_data: исходные данные
    """
    # 1. Парсинг файла
    parser = RD2Parser(filepath)
    result = parser.parse()

    metadata = result['metadata']
    values = result['values']
    timestamps = result['timestamps']

    if len(values) == 0:
        raise ValueError("Файл не содержит данных")

    # 2. Вычисление СКЗ
    analyzer = VibrationAnalyzer()
    rms_result = analyzer.calculate_rms(values)

    # 3. Вычисление спектра
    frequencies, amplitudes = analyzer.calculate_spectrum(
        values,
        metadata['sampling_frequency']
    )

    # 4. Определение зоны
    zone = analyzer.determine_zone(rms_result['total_rms'])

    # 5. Поиск пиков в спектре
    peaks = analyzer.find_spectrum_peaks(frequencies, amplitudes)

    return {
        'metadata': metadata,
        'rms': rms_result,
        'spectrum': {
            'frequencies': frequencies,
            'amplitudes': amplitudes
        },
        'peaks': peaks,
        'zone': zone,
        'raw_data': {
            'timestamps': timestamps,
            'values': values
        }
    }


class RD2ParserFromContent:
    """Парсер для чтения .rd2 из строкового содержимого (для ZIP)."""

    def __init__(self, content: str):
        self.content = content
        self.metadata: Dict = {}
        self.data: Optional[np.ndarray] = None
        self.timestamps: Optional[np.ndarray] = None

    def parse(self) -> Dict:
        """Парсить содержимое."""
        lines = self.content.split('\n')

        # Пропускаем пустые строки в начале
        lines = [l for l in lines if l.strip()]

        if len(lines) < 5:
            raise ValueError("Недостаточно строк в файле")

        # Парсинг заголовка
        self._parse_header(lines[:5])

        # Парсинг данных
        self._parse_data(lines[5:])

        return {
            'metadata': self.metadata,
            'timestamps': self.timestamps,
            'values': self.data
        }

    def _parse_header(self, header_lines: list):
        """Парсинг заголовка файла с поддержкой двух форматов."""
        # Строка 1: Основная информация
        line1 = header_lines[0].strip().split(', ')
        self.metadata['record_number'] = line1[0]
        self.metadata['record_datetime'] = line1[1]
        self.metadata['turbine_id'] = line1[2]
        self.metadata['wtg_id'] = line1[3]
        self.metadata['sensor_name'] = line1[4]

        # Строка 2: Параметры дискретизации
        line2_mapping = {
            'Sampling Time': 'sampling_time',
            'Sampling Frequency': 'sampling_frequency',
            'Samples': 'samples',
            'Duration': 'record_length',
        }
        _parse_key_value_line(self.metadata, header_lines[1], line2_mapping)
        if 'sampling_time' not in self.metadata:
            line2 = header_lines[1].strip().split(', ')
            self.metadata['sampling_time'] = extract_number(line2[0])
            self.metadata['sampling_frequency'] = extract_number(line2[1])
            self.metadata['samples'] = int(extract_number(line2[2]))
            self.metadata['record_length'] = extract_number(line2[4]) if len(line2) > 4 else 0.0
        else:
            self.metadata['sampling_time'] = float(extract_number(self.metadata['sampling_time']))
            self.metadata['sampling_frequency'] = float(extract_number(self.metadata['sampling_frequency']))
            self.metadata['samples'] = int(extract_number(self.metadata['samples']))
            self.metadata['record_length'] = float(extract_number(self.metadata['record_length']))

        # Строка 3: Параметры турбины
        line3_mapping = {
            'Generator Speed': 'generator_speed',
            'Active Power': 'active_power',
            'Wind Speed': 'wind_speed',
            'Cumulative Power': 'cumulative_power',
        }
        _parse_key_value_line(self.metadata, header_lines[2], line3_mapping)
        if 'generator_speed' not in self.metadata:
            line3 = header_lines[2].strip().split(', ')
            self.metadata['generator_speed'] = int(extract_number(line3[0]))
            self.metadata['active_power'] = int(extract_number(line3[1]))
            self.metadata['wind_speed'] = extract_number(line3[2])
            self.metadata['cumulative_power'] = extract_number(line3[4]) if len(line3) > 4 else 0.0
        else:
            self.metadata['generator_speed'] = int(extract_number(self.metadata['generator_speed']))
            self.metadata['active_power'] = int(extract_number(self.metadata['active_power']))
            self.metadata['wind_speed'] = extract_number(self.metadata['wind_speed'])
            self.metadata['cumulative_power'] = extract_number(self.metadata['cumulative_power'])

        # Строка 4: Информация об устройстве
        line4_mapping = {
            'Device': 'device',
            'Serial Number': 'device_serial',
            'MAC': 'mac_address',
            'IP': 'ip_address',
            'FW version': 'firmware_version',
        }
        _parse_key_value_line(self.metadata, header_lines[3], line4_mapping)
        if 'device' not in self.metadata:
            line4 = header_lines[3].strip().split(', ')
            self.metadata['device'] = line4[0].replace('Device: ', '')
            if len(line4) > 1:
                self.metadata['device_serial'] = line4[1].replace('SN: ', '')
            if len(line4) > 2:
                self.metadata['mac_address'] = line4[2].replace('MAC: ', '')
            if len(line4) > 3:
                self.metadata['ip_address'] = line4[3].replace('IP: ', '')
            if len(line4) > 4:
                self.metadata['firmware_version'] = line4[4].replace('FW: ', '')

        # Строка 5: Конфигурация
        line5_mapping = {
            'Number of Configuration': 'config_number',
            'Configuration Table Version': 'config_table_version',
            'Layout Version': 'layout_version',
            'Exception Applied': 'exception_applied',
            'PLC IP Address': 'plc_ip',
        }
        _parse_key_value_line(self.metadata, header_lines[4], line5_mapping)
        if 'config_number' not in self.metadata:
            line5 = header_lines[4].strip().split(', ')
            self.metadata['config_number'] = int(extract_number(line5[0].replace('Config: ', '')))
            if len(line5) > 1:
                self.metadata['config_table_version'] = int(extract_number(line5[1].replace('Table: ', '')))
            if len(line5) > 2:
                self.metadata['layout_version'] = int(extract_number(line5[2].replace('Layout: ', '')))
            if len(line5) > 3:
                self.metadata['exception_applied'] = int(extract_number(line5[3].replace('Exception: ', '')))
            if len(line5) > 4:
                self.metadata['plc_ip'] = line5[4].replace('PLC: ', '')
        else:
            self.metadata['config_number'] = int(extract_number(self.metadata['config_number']))
            self.metadata['config_table_version'] = int(extract_number(self.metadata['config_table_version']))
            self.metadata['layout_version'] = int(extract_number(self.metadata['layout_version']))
            self.metadata['exception_applied'] = int(extract_number(self.metadata['exception_applied']))

    def _parse_data(self, data_lines: list):
        """Парсинг данных вибрации."""
        timestamps = []
        values = []

        for line in data_lines:
            if not line.strip():
                continue

            parts = line.strip().rstrip(',').split(', ')
            if len(parts) >= 3:
                try:
                    timestamps.append(float(parts[1]))
                    values.append(float(parts[2]))
                except (ValueError, IndexError):
                    continue

        self.timestamps = np.array(timestamps)
        self.data = np.array(values)


class MultiSensorRD2Parser:
    """
    Парсер для обработки архивов .zip с данными нескольких датчиков.

    Поддерживает датчики 1-8 с тремя типами фильтров:
    - FILTER (0.1-10 Гц) - НЧ
    - LOW (10-1000 Гц) - ВЧ
    - HIGH (0-12 кГц) - ВЧ(ф)
    """

    def __init__(self, archive_path: str):
        """
        Инициализация парсера архива.

        Args:
            archive_path: Путь к .zip архиву или .rd2 файлу.
        """
        self.archive_path = Path(archive_path)
        self.turbine_metadata: Dict = {}
        self.sensor_data: Dict[int, Dict] = {i: {} for i in range(1, 9)}
        self._parsed = False

    def parse(self) -> bool:
        """
        Парсить архив или файл.

        Returns:
            True если успешно, False иначе.
        """
        try:
            if not self.archive_path.exists():
                raise FileNotFoundError(f"Файл не найден: {self.archive_path}")

            if self.archive_path.suffix.lower() == '.zip':
                return self._parse_zip()
            elif self.archive_path.suffix.lower() == '.rd2':
                return self._parse_single_rd2()
            else:
                raise ValueError(f"Неподдерживаемый формат: {self.archive_path.suffix}")

        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            return False

    def _parse_zip(self) -> bool:
        """Парсить ZIP архив с данными датчиков."""
        with zipfile.ZipFile(self.archive_path, 'r') as zf:
            rd2_files = [f for f in zf.namelist() if f.endswith('.rd2')]

            if not rd2_files:
                raise ValueError("В архиве не найдено файлов .rd2")

            # Группируем файлы по датчикам
            for rd2_file in rd2_files:
                sensor_id = self._extract_sensor_id(rd2_file)
                filter_type = self._extract_filter_type(rd2_file)

                if sensor_id and filter_type:
                    with zf.open(rd2_file) as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        parser = RD2ParserFromContent(content)
                        data = parser.parse()

                        # Сохраняем метаданные турбины из первого файла
                        if not self.turbine_metadata:
                            self.turbine_metadata = data['metadata']

                        # Сохраняем данные датчика
                        if filter_type not in self.sensor_data[sensor_id]:
                            self.sensor_data[sensor_id][filter_type] = {
                                'timestamps': data['timestamps'],
                                'values': data['values'],
                                'metadata': data['metadata']
                            }

            self._parsed = True
            return True

    def _parse_single_rd2(self) -> bool:
        """Парсить одиночный .rd2 файл."""
        parser = RD2Parser(str(self.archive_path))
        data = parser.parse()

        self.turbine_metadata = data['metadata']

        # Определяем тип фильтра из имени файла
        filter_type = self._extract_filter_type(self.archive_path.name)
        sensor_id = self._extract_sensor_id(self.archive_path.name)

        if sensor_id and filter_type:
            self.sensor_data[sensor_id][filter_type] = {
                'timestamps': data['timestamps'],
                'values': data['values'],
                'metadata': data['metadata']
            }

        self._parsed = True
        return True

    def _extract_sensor_id(self, filename: str) -> Optional[int]:
        """Извлечь номер датчика из имени файла."""
        match = re.search(r'SENSOR_(\d{2})', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_filter_type(self, filename: str) -> Optional[str]:
        """Извлечь тип фильтра из имени файла."""
        filename_upper = filename.upper()
        if '_FILTER_' in filename_upper or '_LOW_W' in filename_upper:
            # FILTER = 0.1-10 Гц (НЧ), LOW = 10-1000 Гц (ВЧ)
            if 'LOW' in filename_upper:
                return 'LOW'  # ВЧ 10-1000 Гц
            else:
                return 'FILTER'  # НЧ 0.1-10 Гц
        elif '_HIGH_' in filename_upper:
            return 'HIGH'  # ВЧ(ф) 0-12 кГц
        return None

    def get_turbine_metrics(self) -> Dict:
        """
        Получить метрики турбины из метаданных.

        Returns:
            Словарь с метриками:
            - power_kw: Мощность в кВт
            - generator_speed_rpm: Частота вращения в RPM
            - wind_speed_ms: Скорость ветра в м/с
            - cumulative_power_kwh: Накопленная выработка в кВт·ч
        """
        if not self.turbine_metadata:
            return {
                'power_kw': 0.0,
                'generator_speed_rpm': 0.0,
                'wind_speed_ms': 0.0,
                'cumulative_power_kwh': 0.0
            }

        return {
            'power_kw': float(self.turbine_metadata.get('active_power', 0)),
            'generator_speed_rpm': float(self.turbine_metadata.get('generator_speed', 0)),
            'wind_speed_ms': float(self.turbine_metadata.get('wind_speed', 0)),
            'cumulative_power_kwh': float(self.turbine_metadata.get('cumulative_power', 0))
        }

    def get_sensor_data(self, sensor_id: int) -> Optional[Dict]:
        """
        Получить данные для конкретного датчика.

        Args:
            sensor_id: Номер датчика (1-8).

        Returns:
            Словарь с данными датчика или None.
            Каждый сигнал имеет свой массив времени и частоту дискретизации.
        """
        if not (1 <= sensor_id <= 8):
            return None

        sensor = self.sensor_data.get(sensor_id, {})

        result = {
            'sensor_id': sensor_id,
            'acceleration': None,
            'acceleration_time': None,
            'acceleration_fs': None,
            'velocity': None,
            'velocity_time': None,
            'velocity_fs': None,
            'high_freq': None,
            'high_freq_time': None,
            'high_freq_fs': None,
        }

        # НЧ (0.1-10 Гц) - FILTER
        if 'FILTER' in sensor:
            result['acceleration'] = sensor['FILTER']['values']
            result['acceleration_time'] = sensor['FILTER']['timestamps']
            result['acceleration_fs'] = sensor['FILTER']['metadata'].get('sampling_frequency', 25600)

        # ВЧ (10-1000 Гц) - LOW
        if 'LOW' in sensor:
            result['velocity'] = sensor['LOW']['values']
            result['velocity_time'] = sensor['LOW']['timestamps']
            result['velocity_fs'] = sensor['LOW']['metadata'].get('sampling_frequency', 25600)

        # ВЧ(ф) (0-12 кГц) - HIGH
        if 'HIGH' in sensor:
            result['high_freq'] = sensor['HIGH']['values']
            result['high_freq_time'] = sensor['HIGH']['timestamps']
            result['high_freq_fs'] = sensor['HIGH']['metadata'].get('sampling_frequency', 25600)

        return result

    def get_available_sensors(self) -> List[int]:
        """Получить список доступных датчиков."""
        available = []
        for sensor_id in range(1, 9):
            if self.sensor_data[sensor_id]:
                available.append(sensor_id)
        return available
