# Исправление кириллицы в PDF-отчётах

## Проблема

При экспорте в PDF вместо кириллического текста отображались **чёрные квадраты** (□□□□□).

## Причина

Библиотеки `matplotlib` и `reportlab` по умолчанию используют шрифты без поддержки кириллицы:
- **matplotlib**: стандартный шрифт без Unicode поддержки
- **reportlab**: шрифты семейства Helvetica без кириллической кодировки

## Решение

Используем **стандартные шрифты Windows с поддержкой кириллицы**:
- **Arial** - основной шрифт (есть во всех версиях Windows)
- **Arial-Bold** - для заголовков и жирного текста

### 1. matplotlib (файл `pdf_report_thread.py`)

```python
# НАСТРОЙКА КИРИЛЛИЦЫ ДЛЯ MATPLOTLIB
import matplotlib  # type: ignore[import-not-found]
matplotlib.use('Agg')

# Настройка шрифтов для поддержки кириллицы
# Arial - стандартный шрифт Windows с кириллицей
matplotlib.rcParams['font.family'] = 'Arial'
matplotlib.rcParams['axes.unicode_minus'] = False  # Корректное отображение минуса

import matplotlib.pyplot as plt  # type: ignore[import-not-found]
```

### 2. reportlab (файл `pdf_generator.py`)

```python
# Используем стандартные шрифты Windows
CYRILLIC_FONT_NAME = 'Arial'  # Есть в Windows по умолчанию
CYRILLIC_FONT_BOLD = 'Arial-Bold'

# В стилях:
font_name = 'Arial'
font_bold = 'Arial-Bold'

normal_style = ParagraphStyle(
    'CustomNormal',
    fontName='Arial',  # <-- Стандартный шрифт Windows
    fontSize=10,
    # ...
)
```

## Преимущества Arial

| Шрифт | Windows | Linux | macOS | Кириллица |
|-------|---------|-------|-------|-----------|
| **Arial** | ✅ Встроен | ✅ Обычно есть | ✅ Есть | ✅ Да |
| DejaVu Sans | ❌ Нет | ⚠️ Нужно ставить | ⚠️ Нужно ставить | ✅ Да |
| Helvetica | ⚠️ Нет | ✅ Есть | ✅ Есть | ❌ Нет |

## Установка (не требуется для Windows)

### Windows
**Ничего устанавливать не нужно!** Arial уже есть в системе.

### Linux
```bash
# Шрифты Microsoft (включая Arial)
sudo apt-get install msttcorefonts
# или
sudo yum install msttcorefonts
```

### macOS
Arial предустановлен в macOS.

## Профилактика будущих ошибок

### ✅ При добавлении новых текстовых элементов

1. **matplotlib графики**:
   ```python
   # Всегда настраивайте шрифт в начале функции
   matplotlib.rcParams['font.family'] = 'DejaVu Sans'
   ```

2. **reportlab стили**:
   ```python
   # Используйте глобальную переменную CYRILLIC_FONT_NAME
   from .pdf_generator import CYRILLIC_FONT_NAME
   
   style = ParagraphStyle(
       'MyStyle',
       fontName=CYRILLIC_FONT_NAME,  # <-- Не 'Helvetica'!
       # ...
   )
   ```

3. **Table стили**:
   ```python
   from .pdf_generator import CYRILLIC_FONT_NAME
   
   style_commands = [
       ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT_NAME),
       # ...
   ]
   ```

### ❌ Избегайте

```python
# ПЛОХО: шрифт без кириллицы
fontName='Helvetica'
fontName='Courier'
fontName='Times-Roman'

# ПЛОХО: нет настройки matplotlib
import matplotlib.pyplot as plt
# нет настройки font.family
```

### ✅ Используйте

```python
# ХОРОШО: кириллический шрифт
from .pdf_generator import CYRILLIC_FONT_NAME
fontName=CYRILLIC_FONT_NAME

# ХОРОШО: настройка matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
```

## Тестирование

После изменений всегда проверяйте PDF-отчёт с кириллическим текстом:

1. Загрузите файл `.rd2` или `.zip`
2. Перейдите на вкладку "Отчёты"
3. Нажмите "PDF"
4. Откройте созданный PDF
5. **Проверьте**:
   - Заголовок "Отчёт по вибродиагностике ВЭУ"
   - Названия параметров: "Мощность", "Частота вращения"
   - Названия датчиков: "Датчик 1", "Датчик 2"
   - Зоны: "НЧ RMS", "ВЧ RMS", "ВЧ(ф) RMS"
   - Заключение (длинный текст на русском)

## Известные ограничения

1. **Шрифт DejaVu Sans может отсутствовать** на некоторых системах
   - Решение: используется fallback на Unicode шрифт
   
2. **Спецсимволы (тире, длинные тире)** могут отображаться некорректно
   - Решение: используйте стандартные дефисы `-` вместо `—`

3. **Emoji и редкие Unicode символы** не поддерживаются
   - Решение: избегайте emoji в отчётах

## История изменений

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.4.1 | 2026 | Добавлена поддержка кириллицы в PDF |
| 1.4.2 | 2026 | Улучшена обработка отсутствующих шрифтов |
| 1.4.3 | 2026 | Исправлены ошибки type checking: <br>• Удалены UnicodeFont, IdentityH, _fontdata <br>• Добавлены type ignore для matplotlib <br>• Упрощена регистрация шрифтов (только TTFont) |
| **1.4.4** | **2026** | **Переход на Arial** - стандартный шрифт Windows: <br>• Не требует установки <br>• Есть во всех версиях Windows <br>• Полная поддержка кириллицы |

## Контакты

По вопросам настройки шрифтов обращайтесь к:
- A.Telezhenko (разработчик)
- NLP-Core-Team (Koda assistant)
