# Тесты для KWF Prometheus

## Запуск тестов

### Все тесты
```bash
cd app
python -m pytest tests/ -v
```

### Тесты по модулям
```bash
# Утилиты
python -m pytest tests/test_utils.py -v

# Экспорт
python -m pytest tests/test_exporters.py -v

# Отчёты
python -m pytest tests/test_reports.py -v

# DAL
python -m pytest tests/test_dal.py -v

# Парсеры
python -m pytest tests/test_rd2_parser.py -v
```

### Тесты с фильтрацией
```bash
# Только unit-тесты
python -m pytest tests/ -v -m unit

# Только integration-тесты
python -m pytest tests/ -v -m integration

# Исключая GUI тесты
python -m pytest tests/ -v -m "not gui"
```

### Покрытие кода
```bash
python -m pytest tests/ --cov=kwf_prometheus --cov-report=html
```

## Структура тестов

- `test_utils.py` — тесты утилит (конвертации, анализ вибрации)
- `test_exporters.py` — тесты экспорта (CSV, Excel)
- `test_reports.py` — тесты PDF-отчётов
- `test_dal.py` — тесты слоя доступа к данным
- `test_rd2_parser.py` — тесты парсера RD2 файлов
- `conftest.py` — общие фикстуры

## Статус

- ✅ 41 тест пройден
- ⏭️ 3 теста пропущены (требуют тестовых данных или PostgreSQL)
- ❌ 0 тестов не пройдено
