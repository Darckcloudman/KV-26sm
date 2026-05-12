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
        """Парсинг заголовка файла"""
        
        # Строка 1: Основная информация
        line1 = header_lines[0].strip().split(', ')
        self.metadata['serial_number'] = line1[0]
        self.metadata['timestamp'] = line1[1]
        self.metadata['turbine_id'] = line1[2]
        self.metadata['wtg_id'] = line1[3]
        self.metadata['sensor_name'] = line1[4]
        
        # Строка 2: Параметры дискретизации
        line2 = header_lines[1].strip().split(', ')
        self.metadata['sampling_time'] = float(line2[1])
        self.metadata['sampling_frequency'] = float(line2[4])
        self.metadata['samples'] = int(line2[7])
        self.metadata['duration'] = float(line2[10])
        
        # Строка 3: Параметры турбины
        line3 = header_lines[2].strip().split(', ')
        self.metadata['generator_speed'] = float(line3[1])
        self.metadata['active_power'] = float(line3[4])
        self.metadata['wind_speed'] = float(line3[7])
        self.metadata['cumulative_power'] = float(line3[10])
        
        # Строка 4: Информация об устройстве
        line4 = header_lines[3].strip().split(', ')
        self.metadata['device'] = line4[1]
        self.metadata['device_serial'] = line4[3]
        self.metadata['mac_address'] = line4[5]
        self.metadata['ip_address'] = line4[7]
        self.metadata['firmware_version'] = line4[9]
        
        # Строка 5: Конфигурация
        line5 = header_lines[4].strip().split(', ')
        self.metadata['config_number'] = int(line5[1])
        self.metadata['config_table_version'] = int(line5[3])
        self.metadata['layout_version'] = int(line5[5])
        self.metadata['exception_applied'] = int(line5[7])
        self.metadata['plc_ip'] = line5[9]
    
    def _parse_data(self, data_lines: list):
        """Парсинг данных вибрации"""
        
        timestamps = []
        values = []
        
        for line in data_lines:
            if not line.strip():
                continue
            
            parts = line.strip().split(', ')
            if len(parts) >= 3:
                try:
                    timestamps.append(float(parts[1]))
                    values.append(float(parts[2]))
                except ValueError:
                    continue  # Пропускаем некорректные строки
        
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
            window_size: размер окна для расчёта СКЗ
        
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
        - rms: результаты расчёта СКЗ
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


def main():
    """Пример использования"""
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python rd2_parser.py <путь_к_файлу.rd2>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        result = process_rd2_file(filepath)
        
        print("=" * 60)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА ВИБРОДИАГНОСТИКИ")
        print("=" * 60)
        
        print(f"\n📊 ИНФОРМАЦИЯ О ТУРБИНЕ:")
        print(f"  Турбина: {result['metadata']['turbine_id']}")
        print(f"  WTG ID: {result['metadata']['wtg_id']}")
        print(f"  Датчик: {result['metadata']['sensor_name']}")
        print(f"  Время записи: {result['metadata']['timestamp']}")
        
        print(f"\n🔧 ПАРАМЕТРЫ ИЗМЕРЕНИЯ:")
        print(f"  Частота дискретизации: {result['metadata']['sampling_frequency']} Гц")
        print(f"  Длительность: {result['metadata']['duration']} с")
        print(f"  Количество отсчётов: {result['metadata']['samples']}")
        print(f"  Устройство: {result['metadata']['device']}")
        print(f"  IP: {result['metadata']['ip_address']}")
        
        print(f"\n📈 ВИБРАЦИОННЫЕ ПАРАМЕТРЫ:")
        print(f"  СКЗ (RMS): {result['rms']['total_rms']:.3f} мм/с")
        print(f"  Пиковое значение: {result['rms']['peak']:.3f} мм/с")
        print(f"  Размах: {result['rms']['peak_to_peak']:.3f} мм/с")
        
        print(f"\n🎯 ЗОНА СОСТОЯНИЯ (ISO 10816):")
        zone_colors = {
            'A': '✅ ЗОНА A (Хорошо)',
            'B': '⚠️ ЗОНА B (Удовлетворительно)',
            'C': '⚠️ ЗОНА C (Неудовлетворительно)',
            'D': '❌ ЗОНА D (Критично)'
        }
        print(f"  {zone_colors.get(result['zone'], result['zone'])}")
        
        print(f"\n🔍 ТОП-5 ПИКОВ СПЕКТРА:")
        for i, peak in enumerate(result['peaks'][:5], 1):
            print(f"  {i}. {peak['frequency']:.2f} Гц - {peak['amplitude']:.6f}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
