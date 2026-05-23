# План воссоздания приложения KWF Prometheus в одном EXE файле

## 📋 Резюме проекта

| Параметр | Значение |
|----------|----------|
| **Название** | KWF Prometheus |
| **Тип** | GUI-приложение для анализа вибрационной диагностики |
| **Исходный формат** | Декремилированный PyInstaller EXE (70 MB) |
| **Цель** | Воссоздание функционала в одном EXE файле |
| **Python версия** | 3.12 |
| **GUI фреймворк** | PyQt5 |
| **Визуализация** | matplotlib (backend_qt5agg) |

---

## 🎯 Функциональные требования

### Основные функции
1. **Загрузка файлов .rd2** — выбор одного или нескольких файлов через диалог
2. **Загрузка ZIP-архивов** — автоматическая распаковка и обработка .rd2 файлов
3. **Парсинг метаданных** — извлечение информации о турбине, датчике, параметрах измерения
4. **Расчёт СКЗ (RMS)** — скользящее среднеквадратичное значение с окном 1024 samples
5. **FFT-анализ** — быстрое преобразование Фурье для спектрального анализа
6. **Зонирование по ISO 10816** — оценка состояния (Zone A/B/C/D)
7. **Визуализация спектра** — интерактивные графики с указанием границ зон
8. **Экспорт графиков** — сохранение в PNG формат
9. **Многовкладочный интерфейс** — каждая обработка в отдельной вкладке

### Дополнительные функции
- Обработка клика мышью на графике (координаты, значение)
- Подсветка курсором точек на графике
- Кнопки управления: Загрузить .RD2, Загрузить ZIP, Обработать, Сохранить

---

## 📁 Структура проекта

```
app/
├── PLAN.md                           # Этот файл
├── README.md                         # Инструкция по сборке
├── requirements.txt                  # Зависимости
├── build.spec                        # PyInstaller конфигурация
├── smp12c_vibrodiag/
│   ├── __init__.py
│   ├── main.py                       # Точка входа
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py            # Главное окно PyQt5
│   │   ├── canvas.py                 # MplCanvas для графиков
│   │   └── styles.py                 # CSS стили
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── rd2_parser.py             # Парсер .rd2 файлов
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── vibration_analyzer.py     # Анализатор вибраций
│   └── utils/
│       ├── __init__.py
│       └── file_handler.py           # Работа с файлами и ZIP
└── test_data/                        # Тестовые файлы .rd2 (копии из analysis/)
```

---

## 📅 Этапы разработки

### Этап 1: Подготовка окружения (30 минут)

**Задачи:**
1. Установить Python 3.12+ (если ещё не установлен)
2. Создать виртуальное окружение
3. Установить зависимости

**Команды:**
```powershell
cd D:\Coding\pyton_pro\app
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install numpy scipy pandas matplotlib PyQt5 pyinstaller
```

---

### Этап 2: Создание структуры проекта (15 минут)

**Задачи:**
1. Создать каталоги `smp12c_vibrodiag/gui`, `parsers`, `analysis`, `utils`
2. Создать `__init__.py` в каждом каталоге
3. Скопировать тестовые данные из `analysis/test_data/`

**Команды:**
```powershell
New-Item -ItemType Directory -Force `
    smp12c_vibrodiag/gui, `
    smp12c_vibrodiag/parsers, `
    smp12c_vibrodiag/analysis, `
    smp12c_vibrodiag/utils, `
    test_data

# Скопировать тестовые файлы
Copy-Item "..\analysis\test_data\*.rd2" -Destination "test_data\" -Recurse
```

---

### Этап 3: Реализация парсера .rd2 (1 час)

**Файл:** `smp12c_vibrodiag/parsers/rd2_parser.py`

**Функционал:**
- Класс `RD2Parser` для чтения и парсинга файлов .rd2/.rw2
- Извлечение метаданных из 5 строк заголовка
- Парсинг CSV-подобных данных вибрации
- Валидация формата файла

**Ключевые методы:**
- `parse()` — основная функция, возвращает dict с metadata, timestamps, values
- `_parse_header(lines)` — парсинг заголовка
- `_parse_data(lines)` — парсинг данных вибрации

**Формат заголовка:**
```
38408, 01/09/2025 23:45:29, W1436, WTG37, Sensor_01
Sampling Time, 0.01562500, s, Sampling Frequency, 64, Hz, Samples, 4096, sp,  Duration, 64, s
Generator Speed, 1123, RPM, Active Power, 2334, KW, Wind Speed, 0, m/s, Cumulative Power, 22516386, KWh
Device, 12C, Serial Number, IK2020900086, MAC, 00:0c:f2:00:7c:c0, IP, 192.168.1.37, FW version, 6.0
Number of Configuration, 188, Configuration Table Version, 1802, Layout Version, 8, Exception Applied, 0, PLC IP Address, 192.168.20.37 
```

---

### Этап 4: Реализация анализатора вибраций (1 час)

**Файл:** `smp12c_vibrodiag/analysis/vibration_analyzer.py`

**Классы:**
- `VibrationAnalyzer` — статические методы для анализа

**Методы:**
1. `calculate_rms(values, window_size=1024)` — скользящее СКЗ
   - Возвращает: rms_values (список), total_rms, peak, peak_to_peak
   
2. `calculate_spectrum(values, sampling_freq)` — FFT анализ
   - Возвращает: (frequencies, amplitudes)
   
3. `determine_zone(rms_value)` — определение зоны по ISO 10816
   - Zone A: < 2.3 мм/с (Хорошо)
   - Zone B: 2.3 - 4.5 мм/с (Удовлетворительно)
   - Zone C: 4.5 - 7.8 мм/с (Неудовлетворительно)
   - Zone D: > 7.8 мм/с (Критично)
   
4. `find_spectrum_peaks(frequencies, amplitudes, top_n=10)` — поиск пиков

---

### Этап 5: Реализация GUI на PyQt5 (2 часа)

#### 5.1 MplCanvas (`gui/canvas.py`)
```python
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        super().__init__()
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
    
    def plot_spectrum(self, frequencies, amplitudes, zone):
        # Очистка графика
        # Построение спектра
        # Добавление границ зон (2.3, 4.5, 7.8)
        # Подписи осей и легенда
        pass
    
    def on_click(self, event):
        # Обработка клика — отображение координат
        pass
```

#### 5.2 MainWindow (`gui/main_window.py`)
```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # Создание меню, панелей инструментов
        # QTabWidget для вкладок
        # Кнопки: Загрузить .RD2, Загрузить ZIP, Обработать, Сохранить
        pass
    
    def load_files(self):
        # QFileDialog для выбора .rd2 файлов
        # Добавление в очередь обработки
        pass
    
    def load_zip(self):
        # Выбор ZIP архива
        # Распаковка во временную директорию
        pass
    
    def process(self):
        # Обработка всех загруженных файлов
        # Вызов rd2_parser и vibration_analyzer
        # Создание вкладок с графиками
        pass
    
    def save_graph(self):
        # Сохранение активного графика в PNG
        pass
```

#### 5.3 FileHandler (`utils/file_handler.py`)
```python
class FileHandler:
    @staticmethod
    def unzip(zip_path, dest_dir):
        # Распаковка ZIP архива
        pass
    
    @staticmethod
    def find_rd2_files(directory):
        # Рекурсивный поиск всех .rd2 файлов
        pass
    
    @staticmethod
    def save_graph(fig, filepath):
        # Сохранение графика в PNG
        pass
```

---

### Этап 6: Сборка в EXE (30 минут)

**Файл:** `build.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['smp12c_vibrodiag/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('test_data', 'test_data'),
    ],
    hiddenimports=[
        'numpy',
        'scipy',
        'matplotlib',
        'PyQt5',
        'matplotlib.backends.backend_qt5agg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KWF_Prometheus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KWF_Prometheus',
)

# Для одного EXE файла раскомментировать:
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='KWF_Prometheus',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=False,
# )
```

**Команда сборки:**
```powershell
pyinstaller --clean build.spec
# Или напрямую:
pyinstaller --onefile --windowed --name "KWF_Prometheus" --icon=icon.ico smp12c_vibrodiag/main.py
```

---

### Этап 7: Тестирование и отладка (1 час)

**Тестовые сценарии:**
1. Загрузка одного файла .rd2 → проверка парсинга метаданных
2. Загрузка ZIP с несколькими .rd2 → проверка распаковки
3. Проверка расчёта СКЗ и FFT
4. Проверка определения зоны (A/B/C/D)
5. Проверка отображения графика с границами зон
6. Проверка клика по графику
7. Проверка сохранения PNG

**Тестовые данные:**
- `test_data/SENSOR_01_LOW_W.rd2` — низкочастотные данные (64 Гц)
- `test_data/SENSOR_01_HIGH_W.rd2` — высокочастотные данные
- `test_data/SENSOR_01_FILTER_W.rd2` — отфильтрованные данные

---

## 📦 Зависимости

```txt
# requirements.txt
numpy>=1.24.0,<2.0.0
scipy>=1.10.0,<2.0.0
pandas>=2.0.0,<3.0.0
matplotlib>=3.7.0
PyQt5>=5.15.0
pyinstaller>=6.0.0
python-dateutil>=2.8.0
```

---

## 🎨 Дизайн интерфейса

### Цветовая схема
- Фон графика: белый / светло-серый
- Линия спектра: синий (#1f77b4)
- Граница Zone A/B: оранжевый (#ff7f0e), пунктир
- Граница Zone B/C: красный (#d62728), пунктир
- Граница Zone C/D: тёмно-красный (#9467bd), пунктир

### Размеры
- Основное окно: 1200x800 px
- График: на всю ширину, 400 px высота
- Кнопки: 150x30 px

---

## 📝 Чек-лист готовности

- [ ] Python 3.12+ установлен
- [ ] Все зависимости установлены
- [ ] Парсер .rd2 работает на тестовых данных
- [ ] Анализатор вычисляет СКЗ и FFT корректно
- [ ] GUI отображается без ошибок
- [ ] Загрузка .rd2 файлов работает
- [ ] Загрузка ZIP работает
- [ ] Графики строятся с границами зон
- [ ] Клик по графику отображает координаты
- [ ] Экспорт PNG работает
- [ ] EXE собирается без ошибок
- [ ] EXE запускается на чистой системе

---

## 🚀 Быстрый старт

```powershell
# 1. Перейти в директорию проекта
cd D:\Coding\pyton_pro\app

# 2. Создать и активировать виртуальное окружение
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить приложение (режим разработки)
python -m smp12c_vibrodiag.main

# 5. Собрать EXE
pyinstaller --onefile --windowed --name "KWF_Prometheus" smp12c_vibrodiag/main.py

# 6. Найти EXE в dist/KWF_Prometheus.exe
```

---

## 📚 Ресурсы

- Исходный код из `analysis/rd2_parser.py`
- Документация: `analysis/README.md`
- Reverse engineering: `analysis/APP_EXE_REVERSE_ENGINEERING.md`
- Структура формата: `analysis/structure.md`

---

## 📅 История версий плана

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2025-01-XX | 1.0 | Начальный план на основе анализа |
