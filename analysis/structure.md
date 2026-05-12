# Структура проекта вибродиагностики SMP12C

## Корневая директория: `D:\Сoding\pyton_src\`

### Основные компоненты

```
pyton_src/
├── App Analizer/                 # Скомпилированное приложение (73MB)
│   ├── app.exe                   # Главный исполняемый файл (PyInstaller)
│   └── icon.ico                  # Иконка приложения
│
├── vibro_diag/                   # Исходный код Service Panel SGRE
│   └── Service Panel/
│       ├── CCLink/               # Служба опроса SMP (C# Windows Service)
│       │   └── CCLinkService/
│       │       ├── APC4625_CCLink_Service.exe      # Основной exe
│       │       ├── APC4625_CCLink_Service.exe.config
│       │       ├── APC4626_CCLink_Service_BLL.dll  # Business Logic Layer
│       │       ├── APC4627_CCLink_Service_Common.dll
│       │       ├── APC4925_GestSMPBLL.dll          # Управление SMP
│       │       ├── ServicePanelBusinessLogic.dll
│       │       └── Services/
│       │           ├── ServicePanelBusinessLogic.dll
│       │           └── ServicePanelDataAccess.dll
│       │
│       ├── DBManagementService/  # Управление базой данных
│       │   ├── DBServicePanel.sdf              # SQL CE база данных
│       │   ├── InitialDb.sql                   # Схема БД
│       │   └── bin/
│       │       └── APC4932_ServicePanelDbImportService.exe
│       │
│       ├── Diagnosis/            # Система диагностики (DAS)
│       │   ├── DAS/              # Версия 2 (C# + Python)
│       │   │   ├── APC4702_SP_DASCONTROL_WindowsService.exe
│       │   │   ├── DAS.BUS.dll               # Business Logic
│       │   │   ├── DAS.CFG.dll               # Конфигурация
│       │   │   ├── DAS.Interfaces.dll        # Интерфейсы
│       │   │   └── Services/
│       │   │       └── APC4947_DasControlServices.dll
│       │   │
│       │   └── DASv3/            # Версия 3 (Python-based)
│       │       ├── das.exe                   # Основной exe (LabVIEW?)
│       │       ├── filters/                  # Python фильтры
│       │       │   ├── das_copy.py
│       │       │   └── das_filterGam.py
│       │       ├── scripts/                  # Python скрипты
│       │       │   ├── py_example.py
│       │       │   └── WindCommand/          # Основной движок
│       │       │       ├── CORE/
│       │       │       │   ├── CfgFile.py        # Парсинг конфигурации
│       │       │       │   ├── GamXLoader.py     # Загрузка .gam файлов
│       │       │       │   ├── GamXWriter.py     # Запись .gam файлов
│       │       │       │   ├── MathCalcs.py      # Математические расчёты
│       │       │       │   ├── Target.py         # Целевые значения
│       │       │       │   └── Utils.py          # Утилиты
│       │       │       ├── MODELS/
│       │       │       │   └── G87_2MW.py        # Модель турбины
│       │       │       └── pytransform.py        # Защита кода
│       │       └── wheels/         # Python пакеты (Python 3.4)
│       │           ├── numpy-1.14.5
│       │           ├── scipy-1.1.0
│       │           └── matplotlib-2.2.2
│       │
│       ├── LoadersService/       # Загрузка прошивок SMP
│       │   ├── 12C/                  # SMP12C специфичные библиотеки
│       │   │   ├── APC4342_CH12_SMPConfigurator.dll
│       │   │   └── APC4393_CH12_SMPControl.dll
│       │   ├── 8C/                   # SMP8C специфичные библиотеки
│       │   └── Helpers/              # Общие помощники
│       │       └── APC4337_SMPFwLoader.dll
│       │
│       ├── PremiumFunctionalities/
│       ├── Repository/
│       ├── SPCMDataExchangeService/
│       ├── SPR3WebClient/
│       └── WebClient/
│
├── W1436 WTG37 SMP_20250901_38408_W/  # Тестовые данные
│   ├── *SENSOR_01_LOW_W.rd2          # Низкая частота (64 Гц)
│   ├── *SENSOR_01_HIGH_W.rd2         # Высокая частота
│   └── *SENSOR_01_FILTER_W.rd2       # Отфильтрованные данные
│
├── frontend/                       # React фронтенд (текущий проект)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── TurbineOverview.tsx
│   │   │   └── TurbineDetail.tsx
│   │   └── index.css
│   └── package.json
│
├── img/                            # Скриншоты интерфейса
│   └── app_interface01.PNG
│
└── analysis/                       # Результаты анализа (создаётся)
    ├── structure.md                # Этот файл
    ├── rd2_header_hex.txt          # Hex дамп заголовка
    └── RW2_DECRYPTION_ALGORITHM.md # Алгоритм расшифровки
```

## Ключевые технологии

### C# Components
- **EntityFramework 6.x** - ORM для SQL CE/SQL Server
- **Unity IoC Container** - Dependency Injection
- **log4net** - Логирование
- **Ionic.Zip** - Работа с ZIP архивами
- **SevenZipSharp** - Работа с 7z архивами

### Python Components (DASv3)
- **Python 3.4** (устаревшая версия)
- **numpy** - Математические вычисления
- **scipy** - Обработка сигналов (FFT)
- **matplotlib** - Визуализация
- **pyarmor** - Обфускация кода

### Форматы данных
- **.rd2 / .rw2** - Текстовые файлы вибрационных данных
- **.gam** - Конфигурационные файлы (бинарные)
- **.gamx** - Расширенные конфигурации
- **ZIP** - Архивы с данными от SMP

## Зависимости между компонентами

```
CCLink (C#) → Запрашивает данные с SMP → ZIP с .rd2 файлами
                          ↓
DBManagement → Сохраняет метаданные в SQL CE
                          ↓
DAS (Python) → Расшифровывает .rd2 → Вычисляет СКЗ, FFT
                          ↓
React Frontend → Отображает данные через API
```

## Основные DLL для реверс-инжиниринга

1. **APC4925_GestSMPBLL.dll** - Бизнес-логика управления SMP
2. **APC4342_CH12_SMPConfigurator.dll** - Конфигурация SMP12C
3. **APC4393_CH12_SMPControl.dll** - Управление SMP12C
4. **DAS.BUS.dll** - Бизнес-логика диагностики
5. **ServicePanelBusinessLogic.dll** - Общая бизнес-логика

## Инструменты для анализа

- **ILSpy / dotPeek** - Декомпиляция .NET
- **Hex Editor** - Анализ бинарных файлов
- **Postman / REST Client** - Тестирование API
- **Python 3.11+** - Разработка нового ПО
