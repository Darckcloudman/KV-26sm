# SMP12C VibroDiag Analyzer

GUI-приложение для анализа вибрационной диагностики ветротурбин системы SMP12C (Siemens Gamesa Renewable Energy).

## 🚀 Быстрый старт

### Установка

```powershell
# Перейти в директорию проекта
cd D:\Coding\pyton_pro\app

# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
.\venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt
```

### Запуск в режиме разработки

```powershell
python -m smp12c_vibrodiag.main
```

### Сборка EXE

```powershell
# Вариант 1: Один EXE файл
pyinstaller --onefile --windowed --name "SMP12C_VibroDiag" smp12c_vibrodiag/main.py

# Вариант 2: Использовать build.spec
pyinstaller --clean build.spec
```

Скомпилированный файл будет в папке `dist/SMP12C_VibroDiag.exe`

## 📖 Описание

Приложение предназначено для анализа файлов вибрационной диагностики `.rd2` и `.rw2`, формируемых системами SMP12C на ветротурбинах.

### Возможности

- **Загрузка файлов** — поддержка `.rd2`, `.rw2` и ZIP-архивов с данными
- **Спектральный анализ** — FFT-преобразование для выявления частотных компонент
- **Расчёт СКЗ** — среднеквадратичное значение вибрации
- **Зонирование по ISO 10816** — автоматическая оценка состояния оборудования
- **Интерактивные графики** — клик по графику показывает координаты
- **Экспорт** — сохранение графиков в PNG

### Формат файлов .rd2

Файлы имеют текстовый CSV-подобный формат:

```
38408, 01/09/2025 23:45:29, W1436, WTG37, Sensor_01
Sampling Time, 0.01562500, s, Sampling Frequency, 64, Hz, Samples, 4096, sp,  Duration, 64, s
Generator Speed, 1123, RPM, Active Power, 2334, KW, Wind Speed, 0, m/s, Cumulative Power, 22516386, KWh
Device, 12C, Serial Number, IK2020900086, MAC, 00:0c:f2:00:7c:c0, IP, 192.168.1.37, FW version, 6.0
Number of Configuration, 188, Configuration Table Version, 1802, Layout Version, 8, Exception Applied, 0, PLC IP Address, 192.168.20.37 
0, 0, 0,
1, 0.015625, 0,
...
```

### Зоны состояния (ISO 10816)

| Зона | Диапазон (мм/с) | Состояние |
|------|-----------------|-----------|
| A | < 2.3 | ✅ Хорошее |
| B | 2.3 - 4.5 | ⚠️ Удовлетворительное |
| C | 4.5 - 7.8 | ⚠️ Неудовлетворительное |
| D | > 7.8 | ❌ Критическое |

## 📁 Структура проекта

```
app/
├── PLAN.md                    # Подробный план разработки
├── README.md                  # Этот файл
├── requirements.txt           # Зависимости Python
├── build.spec                 # Конфигурация PyInstaller
├── smp12c_vibrodiag/
│   ├── __init__.py
│   ├── main.py                # Точка входа
│   ├── gui/                   # GUI компоненты
│   ├── parsers/               # Парсеры файлов
│   ├── analysis/              # Анализ вибраций
│   └── utils/                 # Утилиты
└── test_data/                 # Тестовые данные
```

## 🛠️ Технологии

- **Python 3.12**
- **PyQt5** — графический интерфейс
- **matplotlib** — визуализация
- **numpy/scipy** — математические вычисления
- **PyInstaller** — упаковка в EXE

## 📝 Лицензия

Проект создан на основе реверс-инжиниринга декompилированного приложения.

## 📞 Поддержка

Для вопросов обращайтесь к документации в `PLAN.md`.
