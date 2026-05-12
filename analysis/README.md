# Анализ SMP12C вибродиагностики

Этот каталог содержит результаты анализа формата файлов вибродиагностики SMP12C и инструменты для их обработки.

## 📁 Структура

```
analysis/
├── README.md                       # Этот файл
├── structure.md                    # Описание структуры проекта
├── RW2_DECRYPTION_ALGORITHM.md     # Детальный алгоритм расшифровки .rw2/.rd2
├── rd2_parser.py                   # Python-скрипт для анализа файлов
├── run_analysis.ps1                # PowerShell скрипт для запуска
├── rd2_header_hex.txt              # Пример hex-дампа заголовка
└── test_data/                      # Тестовые данные
    └── W1436 WTG37 SMP_20250901_38408_W/
        ├── *SENSOR_01_LOW_W.rd2    # Низкочастотные данные (64 Гц)
        ├── *SENSOR_01_HIGH_W.rd2   # Высокочастотные данные
        └── *SENSOR_01_FILTER_W.rd2 # Отфильтрованные данные
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```powershell
pip install numpy pandas
```

### 2. Запуск анализа

```powershell
# Через PowerShell
.\run_analysis.ps1

# Или напрямую
python rd2_parser.py "путь\к\файлу.rd2"
```

### 3. Использование в коде

```python
from rd2_parser import process_rd2_file

# Обработка файла
result = process_rd2_file("SENSOR_01_LOW_W.rd2")

# Получение результатов
print(f"Зона: {result['zone']}")
print(f"СКЗ: {result['rms']['total_rms']} мм/с")
print(f"Пики спектра: {result['peaks'][:5]}")
```

## 📊 Формат файлов .rd2/.rw2

Файлы имеют **текстовый формат** (не зашифрованы):

```
38408, 01/09/2025 23:45:29, W1436, WTG37, Sensor_01
Sampling Time, 0.01562500, s, Sampling Frequency, 64, Hz, Samples, 4096, sp,  Duration, 64, s
Generator Speed, 1123, RPM, Active Power, 2334, KW, Wind Speed, 0, m/s, Cumulative Power, 22516386, KWh
Device, 12C, Serial Number, IK2020900086, MAC, 00:0c:f2:00:7c:c0, IP, 192.168.1.37, FW version, 6.0
Number of Configuration, 188, Configuration Table Version, 1802, Layout Version, 8, Exception Applied, 0, PLC IP Address, 192.168.20.37 
0, 0, 0,
1, 0.015625, 0,
2, 0.03125, -0.00118709728121758,
...
```

### Типы файлов

| Тип | Частота | Длительность | Отсчётов | Назначение |
|-----|---------|--------------|----------|------------|
| LOW_W.rd2 | 64 Гц | 64 с | 4096 | Низкочастотные вибрации |
| HIGH_W.rd2 | ~5120 Гц | ~1 с | 5120 | Подшипники, шестерни |
| FILTER_W.rd2 | 64 Гц | 64 с | 4096 | Отфильтрованные данные |

## 📈 Метрики

### СКЗ (Root Mean Square)
Вычисляется скользящее СКЗ с окном 1024 отсчёта и перекрытием 50%.

### Зонирование (ISO 10816)

| Зона | Диапазон (мм/с) | Состояние |
|------|-----------------|-----------|
| A | < 2.3 | ✅ Хорошее |
| B | 2.3 - 4.5 | ⚠️ Удовлетворительное |
| C | 4.5 - 7.8 | ⚠️ Неудовлетворительное |
| D | > 7.8 | ❌ Критическое |

### FFT (Быстрое преобразование Фурье)
Вычисляется через `numpy.fft.rfft`. Убирается DC-компонента (0 Гц).

## 🔍 Ключевые выводы

1. **Файлы .rw2/.rd2 НЕ зашифрованы** - это текстовый CSV-подобный формат
2. **Нет необходимости в декомпиляции DLL** - формат полностью открыт
3. **Основная логика:**
   - Парсинг заголовка (5 строк)
   - Чтение CSV-данных
   - Вычисление СКЗ и FFT с помощью numpy/scipy

## 🛠️ Разработка приложения

### Рекомендуемая структура

```
smp12c_vibro_diag/
├── main.py                 # Точка входа
├── smp_client.py           # HTTP клиент для SMP12C
├── rd2_parser.py           # Парсер .rd2 файлов (из этого репо)
├── vibration_analysis.py   # Анализ (СКЗ, FFT)
├── requirements.txt
└── build.spec              # PyInstaller конфигурация
```

### Зависимости

```txt
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
pyinstaller>=6.0.0
```

### Сборка .exe

```powershell
pip install -r requirements.txt
pyinstaller --onefile --windowed main.py
```

## 📞 Взаимодействие с SMP12C

Для получения данных от SMP12C необходимо:

1. **Подключиться к Service Panel** (HTTP API на порту 80/443)
2. **Запросить ZIP-архив** с данными за указанный период
3. **Распаковать архив** - внутри файлы .rd2
4. **Обработать через rd2_parser.py**

### Пример API запроса

```python
import requests

# Подключение к SMP12C
smp_ip = "192.168.1.37"
response = requests.get(f"http://{smp_ip}/api/data/latest")

# Ответ: ZIP архив с .rd2 файлами
with open("vibration_data.zip", "wb") as f:
    f.write(response.content)
```

## 📚 Дополнительные материалы

- [RW2_DECRYPTION_ALGORITHM.md](RW2_DECRYPTION_ALGORITHM.md) - Детальное описание алгоритма
- [structure.md](structure.md) - Структура проекта SGRE
- [dm023660-en.pdf](../dm023660-en.pdf) - Документация (если есть)

## ⚠️ Известные ограничения

1. Python 3.4 в оригинальном DASv3 устарел - рекомендуется Python 3.11+
2. Некоторые DLL в Service Panel обфусцированы - требуется декомпиляция через ILSpy
3. API Service Panel может требовать аутентификацию

## 📝 История изменений

### 2025-05-13
- Проанализирован формат файлов .rd2
- Создан rd2_parser.py
- Проведён тест на реальных данных WTG37
