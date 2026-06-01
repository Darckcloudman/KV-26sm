# Команды для коммита и пуша изменений v1.4.1
# Дата: 2025-01-28

cd D:\Coding\pyton_pro

# 1. Проверить статус (уже выполнено выше)
# git status

# 2. Добавить все изменения
git add .

# 3. Создать коммит
git commit -m "v1.4.1: Компонентная привязка датчиков + Анимированные пики

Новые функции:
- Модель Sensor с компонентной привязкой (редуктор/генератор)
- Миграция БД 004 для component_type ENUM
- Класс BlinkingPeakMarker с мигающими красными точками
- Таблица гармоник с 4 колонками
- Все 10 пиков отображаются на графиках с правильной нумерацией

Исправления:
- TextItem.setFont() вместо font параметра
- Удалён setFill() (не существует)
- SQLAlchemy Inspector type: ignore для has_table/has_column/has_index
- Убран фильтр 5% для пиков на графиках

Документация:
- INTEGRATION_REPORT.md
- MIGRATION_GUIDE.md
- BUGFIX_*.md (4 файла)
- DAILY_SUMMARY_2025_01_28.md"

# 4. Отправить на GitHub
git push origin main

# 5. Создать тег (опционально)
# git tag v1.4.1
# git push origin v1.4.1

# 6. Проверить результат
# git log -1
# git status
