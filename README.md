# KWF Prometheus v1.4.1

GUI-приложение для анализа вибрационной диагностики ветротурбин.

## Что нового в v1.3

### Data Access Layer (DAL)
- Абстрактный репозиторий `IVibrationRepository` с двумя реализациями:
  - `FileSystemRepository` — режим файловой системы (v1.2)
  - `PostgresRepository` — режим PostgreSQL (новый)
- Асинхронный доступ через `asyncpg` + SQLAlchemy 2.0
- Кэширование спектров и результатов анализа
- Утилита миграции `migrate_archives.py`

### Варианты А-Г (2025-01-25 — 2025-01-28)
- **Вариант А**: Исправлен PyQt5 → PySide6, 4 экрана навигации, интеграция с БД
- **Вариант Б**: Логирование в DAL, retry PostgreSQL, поиск в HomeScreen, диалог миграции БД
- **Вариант В**: Экспорт CSV/Excel/PDF, вкладка «Тренды RMS», PDF-отчёты по турбине
- **Вариант Г**: 41 unit-тест, исправления Pydantic, документация

### GUI улучшения (2025-01-25)
- **Новый диалог выбора директории** (`directory_tree_dialog.py`):
  - Древовидный просмотр файловой системы с навигацией
  - Иконки QtAwesome (`mdi.*`) на панели инструментов
  - История Back/Forward, цикличный Home
  - Фиксированный размер `480×530 px`, компактные строки
- **Стилизованные сообщения** (`styled_message_box.py`):
  - Единый серый фон `#5A5A5A` для всех QMessageBox
  - Иконки QtAwesome на заголовках окон
  - Заменены все QMessageBox в проекте
- **PowerShell скрипты** с автоматическим `ExecutionPolicy Bypass` fallback

### Что нового в v1.2

### Экран Home (полная переработка)
- **Интерактивная схема турбины** — `shema.png` с 8 кликабельными индикаторами датчиков
- **Плавно мигающие индикаторы** — `QVariantAnimation` с интерполяцией цвета:
  - `empty` — прозрачный кружок, чёрная рамка (датчик отсутствует)
  - `ok` — зелёная пульсирующая рамка (все сигналы загружены)
  - `partial` — жёлтая пульсирующая рамка (частично загружен)
  - `none` — белый кружок, красная рамка (датчик в файле, но данных нет)
- **Таблица архивов** с кастомным скроллбаром и автосканированием каталога
- **Выбор каталога архивов** через диалог

### Технические изменения
- Переход с **PyQt5** на **PySide6** (современная LTS, лицензия LGPL)
- Чёрная тема интерфейса (`#000000`)

## Что нового в v1.1

- **Исправлена кириллица** — шрифт Geist Sans заменён на Arial с полной поддержкой Unicode
- **Стабильная сборка** — cx_Freeze с корректно включёнными Qt platform plugins
- **Улучшенная надёжность** — отказ от нестабильных шрифтов и зависимостей

## Что нового в v1.0 → v2.0.0

- **Полностью переписанная графика** — matplotlib заменён на нативный QPainter (стабильнее, быстрее, меньше зависимостей)
- **Убраны ненужные зависимости** — pandas, matplotlib удалены
- **Обновлена сборка** — cx_Freeze вместо PyInstaller (совместимость с Python 3.14)

## Быстрый старт

> **PowerShell Execution Policy:** If scripts fail with `PSSecurityException`, use `-ExecutionPolicy Bypass`:
> ```powershell
> powershell.exe -ExecutionPolicy Bypass -File .\install_and_run.ps1
> ```
> Do not change global execution policy (`Set-ExecutionPolicy`) — unsafe.
>
> **Encoding note:** All PowerShell scripts use English text to avoid UTF-8 encoding issues in Windows PowerShell.

### Установка

```powershell
cd D:\Coding\pyton_pro\app
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Запуск в режиме разработки

```powershell
python -m kwf_prometheus.main
```

### Сборка EXE

```powershell
python setup.py build_exe
```

Результат: `build/exe.win-amd64-3.14/KWF_Prometheus.exe`

## Возможности

- **Загрузка файлов** — поддержка `.rd2`, `.rw2` и ZIP-архивов
- **Спектральный анализ** — FFT-преобразование
- **Расчёт СКЗ** — скользящее среднеквадратичное значение
- **Зонирование по ISO 10816** — автоматическая оценка состояния
- **Интерактивные графики** — клик по графику показывает координаты
- **Экран Home** — визуальная схема турбины с индикаторами статуса датчиков
- **Экспорт** — сохранение графиков в PNG

## Зоны состояния (ISO 10816)

| Зона | Диапазон (мм/с) | Состояние |
|------|-----------------|-----------|
| A | < 2.3 | Хорошее |
| B | 2.3 - 4.5 | Удовлетворительное |
| C | 4.5 - 7.8 | Неудовлетворительное |
| D | > 7.8 | Критическое |

## Структура проекта

```
app/
├── README.md                  # Этот файл
├── CHANGELOG_v1.3.md          # История изменений
├── COLORS.md                  # Справочник цветов UI
├── requirements.txt           # Зависимости Python
├── setup.py                   # Конфигурация cx_Freeze
├── PLAN.md                    # Подробный план разработки
├── PROJECT_SUMMARY.md         # Итоговый отчёт
├── kwf_prometheus/
│   ├── __init__.py
│   ├── main.py                # Точка входа
│   ├── app_settings.py        # Настройки приложения
│   ├── gui/                   # GUI компоненты (PySide6)
│   │   ├── main_window.py     # Главное окно
│   │   ├── home_screen.py     # Экран Home
│   │   ├── analysis_data_screen.py  # Экран анализа
│   │   ├── directory_tree_dialog.py # Диалог выбора папки
│   │   ├── styled_message_box.py    # Стилизованные QMessageBox
│   │   ├── metric_card.py
│   │   ├── charts/            # Графики
│   │   └── ...
│   ├── parsers/
│   │   └── rd2_parser.py      # Парсер .rd2 файлов
│   ├── dal/                   # Data Access Layer (NEW)
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── repositories/
│   │   └── alembic/
│   └── utils/
│       └── file_handler.py    # Работа с файлами
└── test_data/                 # Тестовые данные
```

## Технологии

- **Python 3.14**
- **PySide6** — графический интерфейс (Qt6)
- **QtAwesome** — иконки Material Design (`mdi.*`)
- **QPainter** — нативная отрисовка графиков
- **numpy/scipy** — математические вычисления
- **PostgreSQL + asyncpg** — хранение данных (опционально)
- **cx_Freeze** — упаковка в EXE

## Лицензия

Проект создан на основе реверс-инжиниринга декомпилированного приложения.

## 📄 Документация

- [DAL_GUIDE.md](DAL_GUIDE.md) - полное руководство по DAL
- [GETTING_STARTED.md](GETTING_STARTED.md) - быстрый старт
- [DEVELOPMENT_GUIDELINES.md](DEVELOPMENT_GUIDELINES.md) - руководство разработчика (стили, иконки, архитектура)
