# Исправление кириллицы в PDF-отчётах

## Проблема

При экспорте в PDF вместо кириллического текста отображались **чёрные квадраты** (□□□□□).

## Причина

Библиотеки `matplotlib` и `reportlab` по умолчанию используют шрифты без поддержки кириллицы:
- **matplotlib**: стандартный шрифт без Unicode поддержки
- **reportlab**: шрифты семейства Helvetica без кириллической кодировки

## Решение

### 1. matplotlib (файл `pdf_report_thread.py`)

```python
# НАСТРОЙКА КИРИЛЛИЦЫ ДЛЯ MATPLOTLIB
import matplotlib
matplotlib.use('Agg')

# Настройка шрифтов для поддержки кириллицы
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False  # Корректное отображение минуса

import matplotlib.pyplot as plt

# При сохранении указываем кодировку
fig.savefig(temp_path, bbox_inches='tight', dpi=100, encoding='utf-8')
```

### 2. reportlab (файл `pdf_generator.py`)

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeFont, IdentityH

def _setup_cyrillic_fonts():
    """Настроить шрифты с поддержкой кириллицы."""
    # Попытка зарегистрировать DejaVu Sans
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/DejaVuSans.ttf',
        # ... другие пути
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
            return 'DejaVuSans'
    
    # Fallback: Unicode шрифт
    unicode_font = UnicodeFont('Unicode', IdentityH())
    pdfmetrics.registerFont(unicode_font)
    return 'Unicode'

# Глобальная инициализация
CYRILLIC_FONT_NAME = _setup_cyrillic_fonts()

# Использование в стилях
font_name = CYRILLIC_FONT_NAME or 'Helvetica'
normal_style = ParagraphStyle(
    'CustomNormal',
    fontName=font_name,  # <-- Используем кириллический шрифт
    fontSize=10,
    # ...
)
```

## Установленные шрифты

### Linux
```bash
sudo apt-get install fonts-dejavu-core
# или
sudo yum install dejavu-sans-fonts
```

### Windows
Шрифт DejaVu Sans необходимо установить вручную:
1. Скачать с https://dejavu-fonts.github.io/
2. Установить в `C:\Windows\Fonts\`

### macOS
```bash
brew install --cask font-dejavu
```

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

## Контакты

По вопросам настройки шрифтов обращайтесь к:
- A.Telezhenko (разработчик)
- NLP-Core-Team (Koda assistant)
