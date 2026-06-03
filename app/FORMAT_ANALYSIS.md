# Анализ формата файлов .rd2/.rw2 SMP12C

## 📋 Общая информация

Файлы вибродиагностики SMP12C имеют **текстовый формат** (не зашифрованы) и представляют собой CSV-подобную структуру.

## 📁 Структура файла

### Заголовок (5 строк)

```
38408, 01/09/2025 23:45:29, W1436, WTG37, Sensor_01
Sampling Time, 0.01562500, s, Sampling Frequency, 64, Hz, Samples, 4096, sp,  Duration, 64, s
Generator Speed, 1123, RPM, Active Power, 2334, KW, Wind Speed, 0, m/s, Cumulative Power, 22516386, KWh
Device, 12C, Serial Number, IK2020900086, MAC, 00:0c:f2:00:7c:c0, IP, 192.168.1.37, FW version, 6.0
Number of Configuration, 188, Configuration Table Version, 1802, Layout Version, 8, Exception Applied, 0, PLC IP Address, 192.168.20.37 
```

#### Строка 1: Основная информация
| Поле | Значение | Описание |
|------|----------|----------|
| 0 | 38408 | Серийный номер датчика |
| 1 | 01/09/2025 23:45:29 | Дата и время записи |
| 2 | W1436 | ID турбины |
| 3 | WTG37 | ID ветрогенератора |
| 4 | Sensor_01 | Имя датчика |

#### Строка 2: Параметры дискретизации
| Поле | Значение | Описание |
|------|----------|----------|
| Sampling Time | 0.01562500 с | Время дискретизации |
| Sampling Frequency | 64 Гц | Частота дискретизации |
| Samples | 4096 sp | Количество отсчётов |
| Duration | 64 с | Длительность записи |

#### Строка 3: Параметры турбины
| Поле | Значение | Описание |
|------|----------|----------|
| Generator Speed | 1123 RPM | Скорость генератора |
| Active Power | 2334 KW | Активная мощность |
| Wind Speed | 0 m/s | Скорость ветра |
| Cumulative Power | 22516386 KWh | Накопленная энергия |

#### Строка 4: Информация об устройстве
| Поле | Значение | Описание |
|------|----------|----------|
| Device | 12C | Модель устройства (SMP12C) |
| Serial Number | IK2020900086 | Серийный номер |
| MAC | 00:0c:f2:00:7c:c0 | MAC-адрес |
| IP | 192.168.1.37 | IP-адрес |
| FW version | 6.0 | Версия прошивки |

#### Строка 5: Конфигурация
| Поле | Значение | Описание |
|------|----------|----------|
| Number of Configuration | 188 | Номер конфигурации |
| Configuration Table Version | 1802 | Версия таблицы конфигурации |
| Layout Version | 8 | Версия макета |
| Exception Applied | 0 | Применено исключение |
| PLC IP Address | 192.168.20.37 | IP-адрес PLC |

### Данные вибрации

После заголовка следуют строки с данными в формате:

```
<index>, <timestamp>, <value>,
```

Пример:
```
0, 0, 0,
1, 0.015625, 0,
2, 0.03125, -0.00118709728121758,
3, 0.046875, -0.00237419456243516,
...
```

| Поле | Тип | Описание |
|------|-----|----------|
| index | int | Порядковый номер отсчёта |
| timestamp | float | Время в секундах |
| value | float | Значение виброскорости (мм/с) |

## 📊 Типы файлов

| Тип файла | Частота | Длительность | Отсчётов | Назначение |
|-----------|---------|--------------|----------|------------|
| `*_LOW_W.rd2` | 64 Гц | 64 с | 4096 | Низкочастотные вибрации |
| `*_HIGH_W.rd2` | ~5120 Гц | ~1 с | 5120 | Подшипники, шестерни |
| `*_FILTER_W.rd2` | 64 Гц | 64 с | 4096 | Отфильтрованные данные |

## 🔍 Методы анализа

### 1. Расчёт СКЗ (RMS)

```python
import numpy as np

def calculate_rms(values, window_size=1024):
    """Скользящее СКЗ с перекрытием 50%"""
    step = window_size // 2
    rms_values = []
    
    for i in range(0, len(values) - window_size, step):
        window = values[i:i + window_size]
        rms = np.sqrt(np.mean(window ** 2))
        rms_values.append(rms)
    
    return rms_values
```

### 2. FFT анализ

```python
def calculate_spectrum(values, sampling_freq):
    """Спектр через быстрое преобразование Фурье"""
    n = len(values)
    fft_result = np.fft.rfft(values)
    frequencies = np.fft.rfftfreq(n, d=1/sampling_freq)
    amplitudes = np.abs(fft_result) * 2 / n
    
    # Убираем DC компоненту
    return frequencies[1:], amplitudes[1:]
```

### 3. Теорема Найквиста-Котельникова

**Важно:** Максимальная частота в спектре ограничена частотой Найквиста:

```
F_nyquist = Fs / 2
```

где `Fs` — частота дискретизации из метаданных файла.

| Тип файла | Fs (Гц) | F_nyquist (Гц) | Макс. пик |
|-----------|---------|----------------|-----------|
| `*_LOW_W.rd2` | 64 | 32 | 32 Гц |
| `*_FILTER_W.rd2` | 2560 | 1280 | 1280 Гц |
| `*_HIGH_W.rd2` | 10240 | 5120 | 5120 Гц |

**Практическое правило:** Все пики в спектре должны быть ≤ `F_nyquist`. Если пик имеет частоту выше — это ошибка интерпретации данных.

```python
# Проверка валидности пиков
nyquist = sampling_freq / 2
valid_peaks = [p for p in peaks if p['frequency'] <= nyquist]
```

📖 **Подробная документация:** см. [NYQUIST_FFT_THEORY.md](../kwf_prometheus/docs/NYQUIST_FFT_THEORY.md)

### 3. Зонирование по ISO 10816

#### Виброскорость (ВЧ, 10-1000 Гц)

| Зона | Диапазон (мм/с) | Состояние |
|------|-----------------|-----------|
| A | < 2.3 | ✅ Хорошее |
| B | 2.3 - 4.5 | ⚠️ Удовлетворительное |
| C | 4.5 - 7.8 | ⚠️ Неудовлетворительное |
| D | > 7.8 | ❌ Критическое |

#### Виброускорение (НЧ, 0.1-10 Гц)

| Зона | Диапазон (м/с²) | Состояние |
|------|-----------------|-----------|
| A | < 1.0 | ✅ Хорошее |
| B | 1.0 - 2.5 | ⚠️ Удовлетворительное |
| C | 2.5 - 5.0 | ⚠️ Неудовлетворительное |
| D | > 5.0 | ❌ Критическое |

## 🛠️ Инструменты для работы

### Парсинг файла

```python
from rd2_parser import process_rd2_file

result = process_rd2_file("SENSOR_01_LOW_W.rd2")

# Метаданные
print(result['metadata']['turbine_id'])
print(result['metadata']['sampling_frequency'])

# Результаты анализа
print(f"Зона: {result['zone']}")
print(f"СКЗ: {result['rms']['total_rms']:.3f} мм/с")
print(f"Пики спектра: {result['peaks'][:5]}")
```

### Визуализация

```python
import matplotlib.pyplot as plt

frequencies = result['spectrum']['frequencies']
amplitudes = result['spectrum']['amplitudes']

plt.plot(frequencies, amplitudes)
plt.axhline(y=2.3, color='orange', linestyle='--')
plt.axhline(y=4.5, color='red', linestyle='--')
plt.xlabel('Частота, Гц')
plt.ylabel('Амплитуда, мм/с')
plt.show()
```

## 📝 Примеры использования

### Обработка ZIP архива

```python
import zipfile
from pathlib import Path

# Распаковка
with zipfile.ZipFile('data.zip', 'r') as zip_ref:
    zip_ref.extractall('extracted/')

# Поиск .rd2 файлов
rd2_files = list(Path('extracted/').rglob('*.rd2'))

# Обработка
for filepath in rd2_files:
    result = process_rd2_file(str(filepath))
    print(f"{filepath.name}: Зона {result['zone']}")
```

## ⚙️ Технические детали

### Кодировка
- UTF-8

### Разделитель
- `, ` (запятая + пробел)

### Перенос строки
- `\n` (Unix) или `\r\n` (Windows)

### Числовой формат
- Float: IEEE 754 double precision
- Форматирование: произвольная точность

## 📚 Дополнительные ресурсы

- [ISO 10816](https://www.iso.org/standard/17947.html) — Стандарт оценки вибрации
- [numpy.fft](https://numpy.org/doc/stable/reference/routines.fft.html) — FFT библиотека
- [matplotlib](https://matplotlib.org/) — Визуализация
