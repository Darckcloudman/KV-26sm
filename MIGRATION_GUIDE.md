# Руководство по миграциям БД

## Обновление схемы БД для v1.4.1+

### Что нового в миграции 004

1. **Добавлена привязка датчиков к компонентам:**
   - Датчики 1-5: Редуктор (Gearbox)
   - Датчики 6-8: Генератор (Generator)

2. **Создана таблица `sensor_configurations`:**
   - Хранит конфигурации датчиков для разных моделей турбин
   - Позволяет гибко настраивать частотные диапазоны

3. **Добавлен тип ENUM `component_type`:**
   - `gearbox` — редуктор
   - `generator` — генератор
   - `other` — другое

### Выполнение миграций

```powershell
# 1. Активировать виртуальное окружение
.\venv\Scripts\Activate.ps1

# 2. Перейти в директорию DAL
cd kwf_prometheus\dal

# 3. Проверить текущую версию миграции
alembic current

# 4. Выполнить все миграции до HEAD
alembic upgrade head

# 5. Проверить статус
alembic history
```

### Откат миграции (если нужно)

```powershell
# Откатить на одну версию назад
alembic downgrade -1

# Откатить до конкретной ревизии
alembic downgrade 003

# Откатить до начала (ОПАСНО! удаляет все данные)
alembic downgrade base
```

### Проверка миграции

```python
# Тестовый скрипт для проверки
python -c "
from kwf_prometheus.dal.models import Sensor, ComponentType

# Проверка статических методов
print('Датчики редуктора:', Sensor.get_gearbox_sensors())
print('Датчики генератора:', Sensor.get_generator_sensors())
print('Тип для позиции 3:', Sensor.get_component_type_for_position(3).value)
print('Тип для позиции 7:', Sensor.get_component_type_for_position(7).value)
"
```

### Ожидаемый вывод

```
Датчики редуктора: [1, 2, 3, 4, 5]
Датчики генератора: [6, 7, 8]
Тип для позиции 3: gearbox
Тип для позиции 7: generator
```

---

## Структура БД после миграции 004

### Таблица `sensors`

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | SERIAL | Первичный ключ |
| turbine_id | INT | Ссылка на турбину |
| position_code | INT | Позиция датчика (1-8) |
| description | VARCHAR(200) | Описание позиции |
| component_type | ENUM | Тип компонента (gearbox/generator) |
| sensor_type | VARCHAR(50) | Тип датчика (acceleration/velocity) |
| frequency_range_low | FLOAT | Нижняя граница частот (Гц) |
| frequency_range_high | FLOAT | Верхняя граница частот (Гц) |
| is_active | BOOLEAN | Активен ли датчик |
| created_at | TIMESTAMP | Дата создания |

### Таблица `sensor_configurations`

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | SERIAL | Первичный ключ |
| turbine_model | VARCHAR(50) | Модель турбины |
| position_code | INT | Позиция датчика |
| component_type | ENUM | Тип компонента |
| description | VARCHAR(200) | Описание |
| sensor_type | VARCHAR(50) | Тип датчика |
| frequency_range_low | FLOAT | Нижняя граница частот |
| frequency_range_high | FLOAT | Верхняя граница частот |

---

**Дата:** 2025-01-28  
**Версия миграции:** 004
