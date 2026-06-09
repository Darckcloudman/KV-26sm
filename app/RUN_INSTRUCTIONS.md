# Инструкция по запуску KWF Prometheus v1.4.3

## Быстрый запуск

### Вариант 1: Через run_app.bat (Рекомендуется)
D:\Coding\pyton_pro\run_app.bat

Что делает:
1. Автоматически синхронизирует версии между директориями
2. Очищает кэш Python (__pycache__)
3. Проверяет версию приложения (1.4.3)
4. Запускает актуальную версию
5. Показывает ошибки при возникновении

### Вариант 2: Ручной запуск
cd D:\Coding\pyton_pro\app
python -m kwf_prometheus.main

### Вариант 3: Ручная очистка кэша + запуск
D:\Coding\pyton_pro\app\scripts\clean_cache.bat
python -m kwf_prometheus.main

### Вариант 4: Ручная синхронизация версий
D:\Coding\pyton_pro\app\scripts\sync_versions.bat
python -m kwf_prometheus.main

---

## Очистка кэша (PowerShell)
cd D:\Coding\pyton_pro\app
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" -File | Remove-Item -Force

---

## Проверка версии
После запуска проверьте версию в заголовке окна приложения.

---

## Примечания
- Кэш Python может вызывать запуск старой версии кода
- run_app.bat автоматически очищает кэш при каждом запуске
- Версия 1.4.3 указана в: main.py, setup.py, pyproject.toml, CHANGELOG.md

Версия инструкции: 1.0
Дата: 2025-01-28
Актуальная версия приложения: 1.4.3
