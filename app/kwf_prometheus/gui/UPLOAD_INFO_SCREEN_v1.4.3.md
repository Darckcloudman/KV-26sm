# Вкладка "Информация о загрузке" v1.4.3

## ✨ Новые возможности

### 1. Обновлённый интерфейс
- **Название ВЭУ**: Только WTGxx (без префикса "ВЭУ:")
- **Параметры записи**: В одной строке через "|"
- **Селектор датчиков**: С подсветкой статусов

### 2. Статусы датчиков (цветовая индикация)
- 🟢 **Зелёный** (#00C853): Все 3 файла загружены (FILTER, HIGH, LOW)
- 🟠 **Оранжевый** (#FFC107): Частичная загрузка (1-2 файла)
- 🔴 **Красный** (#DD2C00): Датчик отсутствует

### 3. Графики

#### Левая панель: ВЧ(ф) СПЕКТР (3D)
- **Оси**: Дата (X), Гц (Y), Амплитуда (Z - размер/цвет точки)
- **Данные**: За последние 4 месяца
- **Цвет**: Градиент от зелёного (низкая) к красному (высокая)
- **Оптимизация**: До 500 точек для производительности

#### Правая панель: КОЛИЧЕСТВО ЗАПИСЕЙ (4 месяца)
- **Тип**: Гистограмма
- **Данные**: Количество архивов по дням
- **Период**: Последние 120 дней
- **Стиль**: Градиентный столбец

## 🔧 Технические детали

### Workers
1. **StatisticsWorker**: Загрузка статистики + timeline
2. **SpectrumDataWorker**: Загрузка данных ВЧ(ф) для 3D графика

### Методы БД
- get_records_timeline(wtg_id, start_date, end_date)
- get_vh_spectrum_data(wtg_id, sensor_id, start_date, end_date)

### Классы
- SensorSelector: Панель выбора датчиков
- Spectrum3DChart: 3D визуализация спектра
- RecordsChart: Гистограмма записей
- UploadInfoScreen: Основной экран

## 📁 Файлы
- kwf_prometheus/gui/upload_info_screen.py (обновлён)
- kwf_prometheus/gui/workers/spectrum_worker.py (новый)
- kwf_prometheus/gui/workers/statistics_worker.py (обновлён)
- kwf_prometheus/dal/repositories/postgres.py (обновлён)
- kwf_prometheus/dal/repositories/base.py (обновлён)

## 🚀 Использование

`python
# Создание экрана
screen = UploadInfoScreen(repository=self.repository, parent=self)

# Установка данных
screen.set_upload_data(
    turbine_name="WTG56",
    loaded_sensors={1: {...}, 2: {...}},
    sensor_files={1: {'FILTER': '...', 'HIGH': '...', 'LOW': '...'}},
    generator_speed="1123 RPM",
    active_power="2334 KW",
    record_length="64 s",
    record_number="00001",
    record_datetime="2025-01-28 12:00:00"
)

# Callbacks
screen.set_callbacks(
    on_back=self.go_back,
    on_process=self.process_data
)
`

## ⚠️ Примечания
- Для работы с БД требуется settings.use_database = True
- FileSystemRepository возвращает пустые данные для графиков
- Оптимизация: максимум 500 точек на 3D графике
