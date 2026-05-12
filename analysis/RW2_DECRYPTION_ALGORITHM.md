# Алгоритм расшифровки файлов .rw2/.rd2 SMP12C

## 1. Общая информация о формате

Файлы `.rw2` и `.rd2` имеют **текстовый формат** с CSV-подобной структурой. Это не бинарные зашифрованные файлы, а структурированные текстовые данные, экспортированные из системы вибродиагностики SMP12C.

### 2. Структура файла

#### 2.1 Заголовок (5 строк)

```
<Serial Number>, <Timestamp>, <Turbine ID>, <WTG ID>, <Sensor Name>
Sampling Time, <value>, s, Sampling Frequency, <value>, Hz, Samples, <value>, sp, Duration, <value>, s
Generator Speed, <value>, RPM, Active Power, <value>, KW, Wind Speed, <value>, m/s, Cumulative Power, <value>, KWh
Device, <Model>, Serial Number, <Serial>, MAC, <MAC>, IP, <IP>, FW version, <Version>
Number of Configuration, <value>, Configuration Table Version, <value>, Layout Version, <value>, Exception Applied, <value>, PLC IP Address, <IP>
```

**Пример:**
```
38408, 01/09/2025 23:45:29, W1436, WTG37, Sensor_01
Sampling Time, 0.01562500, s, Sampling Frequency, 64, Hz, Samples, 4096, sp,  Duration, 64, s
Generator Speed, 1123, RPM, Active Power, 2334, KW, Wind Speed, 0, m/s, Cumulative Power, 22516386, KWh
Device, 12C, Serial Number, IK2020900086, MAC, 00:0c:f2:00:7c:c0, IP, 192.168.1.37, FW version, 6.0
Number of Configuration, 188, Configuration Table Version, 1802, Layout Version, 8, Exception Applied, 0, PLC IP Address, 192.168.20.37 
```

#### 2.2 Тело данных

После заголовка следуют строки с данными в формате:
```
<Sample Index>, <Timestamp>, <Value>
```

**Пример:**
```
0, 0, 0,
1, 0.015625, 0,
2, 0.03125, -0.00118709728121758,
3, 0.046875, -0.0130580700933933,
4, 0.0625, -0.03917421028018,
...
```

**Поля:**
- **Sample Index** - номер отсчёта (0, 1, 2, ...)
- **Timestamp** - время в секундах от начала записи
- **Value** - значение виброскорости (мм/с или м/с² в зависимости от типа датчика)

## 3. Типы файлов

### 3.1 LOW_W.rd2 - Низкочастотные данные
- **Частота дискретизации:** 64 Гц
- **Длительность:** 64 секунды
- **Количество отсчётов:** 4096
- **Применение:** Анализ низкочастотных вибраций (балансировка,Misalignment)

### 3.2 HIGH_W.rd2 - Высокочастотные данные
- **Частота дискретизации:** ~5120 Гц (зависит от конфигурации)
- **Применение:** Анализ подшипников качения, зубчатых передач

### 3.3 FILTER_W.rd2 - Отфильтрованные данные
- Содержит данные после применения цифровых фильтров
- Используется для выделения специфических частотных компонент

## 4. Алгоритм чтения файла (Python)

```python
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional

class RD2Parser:
    """Парсер файлов .rd2/.rw2 SMP12C"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.metadata: Dict = {}
        self.data: Optional[np.ndarray] = None
        self.timestamps: Optional[np.ndarray] = None
        
    def parse(self) -> Dict:
        """
        Основная функция парсинга
        Возвращает словарь с метаданными и данными
        """
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
                timestamps.append(float(parts[1]))
                values.append(float(parts[2]))
        
        self.timestamps = np.array(timestamps)
        self.data = np.array(values)
```

## 5. Вычисление СКЗ (Root Mean Square)

```python
def calculate_rms(values: np.ndarray, window_size: int = 1024) -> Dict:
    """
    Вычисление скользящего СКЗ
    
    Args:
        values: массив значений виброскорости
        window_size: размер окна для расчёта СКЗ
    
    Returns:
        словарь с результатами
    """
    # Скользящее СКЗ
    rms_values = []
    step = window_size // 2  # Перекрытие 50%
    
    for i in range(0, len(values) - window_size, step):
        window = values[i:i + window_size]
        rms = np.sqrt(np.mean(window ** 2))
        rms_values.append({
            'timestamp': i * step,
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
```

## 6. Вычисление FFT (Быстрое преобразование Фурье)

```python
def calculate_spectrum(values: np.ndarray, sampling_freq: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Вычисление спектрa через FFT
    
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
```

## 7. Зонирование состояния (ISO 10816)

```python
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
```

## 8. Полный алгоритм обработки

```python
def process_rd2_file(filepath: str) -> Dict:
    """
    Полный алгоритм обработки файла .rd2
    
    Args:
        filepath: путь к файлу
    
    Returns:
        словарь со всеми результатами
    """
    # 1. Парсинг файла
    parser = RD2Parser(filepath)
    result = parser.parse()
    
    metadata = result['metadata']
    values = result['values']
    timestamps = result['timestamps']
    
    # 2. Вычисление СКЗ
    rms_result = calculate_rms(values)
    
    # 3. Вычисление спектра
    frequencies, amplitudes = calculate_spectrum(
        values, 
        metadata['sampling_frequency']
    )
    
    # 4. Определение зоны
    zone = determine_zone(rms_result['total_rms'])
    
    return {
        'metadata': metadata,
        'rms': rms_result,
        'spectrum': {
            'frequencies': frequencies,
            'amplitudes': amplitudes
        },
        'zone': zone,
        'raw_data': {
            'timestamps': timestamps,
            'values': values
        }
    }
```

## 9. Пример использования

```python
# Обработка файла
result = process_rd2_file(
    'W1436 WTG37 SMP_20250901_38408_SENSOR_01_LOW_W.rd2'
)

print(f"Турбина: {result['metadata']['turbine_id']}")
print(f"Датчик: {result['metadata']['sensor_name']}")
print(f"СКЗ: {result['rms']['total_rms']:.2f} мм/с")
print(f"Зона: {result['zone']}")
print(f"Пик: {result['rms']['peak']:.2f} мм/с")
print(f"Частоты спектра: {len(result['spectrum']['frequencies'])} точек")
```

## 10. Выводы

1. **Файлы .rw2/.rd2 НЕ зашифрованы** - это текстовый формат
2. **Нет необходимости в декомпиляции DLL** - формат полностью открыт
3. **Основная логика обработки:**
   - Парсинг заголовка (5 строк)
   - Чтение CSV-подобных данных
   - Вычисление СКЗ и FFT с помощью numpy/scipy
4. **Ключевые параметры:**
   - Частота дискретизации: 64 Гц (LOW), ~5120 Гц (HIGH)
   - Длительность: 64 секунды
   - Количество отсчётов: 4096 (LOW)

## 11. Рекомендации по разработке

Для создания автономного .exe приложения:

1. **Использовать Python 3.11+** с библиотеками:
   - `numpy` - математика
   - `scipy` - FFT
   - `pandas` - обработка данных
   - `pyinstaller` - упаковка в .exe

2. **Алгоритм работы приложения:**
   - Подключение к SMP12C по HTTP (Service Panel API)
   - Загрузка ZIP-архивов с .rd2 файлами
   - Парсинг файлов через RD2Parser
   - Вычисление СКЗ, FFT
   - Определение зон
   - Визуализация через React frontend

3. **Структура проекта:**
   ```
   smp12c_vibro_diag/
   ├── main.py                 # Точка входа
   ├── smp_client.py           # HTTP клиент для SMP
   ├── rd2_parser.py           # Парсер .rd2 файлов
   ├── vibration_analysis.py   # Анализ (СКЗ, FFT)
   ├── requirements.txt
   └── build.spec              # PyInstaller конфигурация
   ```
