# -*- coding: utf-8 -*-
"""
Единая система стилей UI для SMP12C VibroDiag Analyzer v1.3

Основана на чёрно-белой минималистичной теме HomeScreen.
Все экраны должны использовать эти стили для консистентности.
"""

import base64
import os

# === ЦВЕТОВАЯ ПАЛИТРА ===

# Основные цвета
COLOR_BG_PRIMARY = "#000000"      # Основной фон (главные экраны)
COLOR_BG_SECONDARY = "#1A1A1A"    # Вторичный фон (таблицы, панели)
COLOR_BG_TERTIARY = "#2A2A2A"     # Третичный фон (заголовки таблиц, кнопки)
COLOR_BG_DARK = "#0A0A0A"         # Тёмный фон (панели сырых данных)

# Цвета текста
COLOR_TEXT_PRIMARY = "#FFFFFF"    # Основной текст (заголовки, важные данные)
COLOR_TEXT_SECONDARY = "#BBBBBB"  # Вторичный текст (описания)
COLOR_TEXT_TERTIARY = "#888888"   # Третичный текст (подписи, второстепенное)
COLOR_TEXT_DISABLED = "#666666"   # Неактивный текст
COLOR_TEXT_MUTED = "#444444"      # Приглушённый текст (версия, футер)

# Цвета акцентов
COLOR_ACCENT = "#FFFFFF"          # Акцент (кнопки, выделение)
COLOR_ACCENT_HOVER = "#E8E8E8"    # Акцент при наведении
COLOR_ACCENT_PRESSED = "#D0D0D0"  # Акцент при нажатии

# Цвета границ
COLOR_BORDER = "#333333"          # Основные границы
COLOR_BORDER_LIGHT = "#424242"    # Светлые границы
COLOR_BORDER_SUBTLE = "#2A2A2A"   # Тонкие границы

# Цвета зон ISO 10816
ZONE_COLORS = {
    'A': '#00C853',   # Зелёный — норма
    'B': '#FFD600',   # Жёлтый — внимание
    'C': '#FF6D00',   # Оранжевый — требует внимания
    'D': '#DD2C00',   # Красный — критично
    '-': '#424242',   # Серый — нет данных
}

# Цвета статусов датчиков
STATUS_COLORS = {
    'empty': '#000000',    # Чёрный — датчик отсутствует
    'ok': '#4CAF50',       # Зелёный — все сигналы загружены
    'partial': '#FFC107',  # Жёлтый — частично загружен
    'none': '#F44336',     # Красный — данных нет
}


# === ШРИФТЫ ===

FONT_FAMILY = "Arial"           # Основной шрифт (кириллица)
FONT_FAMILY_MONO = "Consolas"   # Моноширинный (графики, данные)

# Размеры шрифтов
FONT_SIZE_TITLE = 22            # Заголовки экранов
FONT_SIZE_HEADING = 16          # Заголовки разделов
FONT_SIZE_SUBHEADING = 14       # Подзаголовки
FONT_SIZE_BODY = 12             # Основной текст
FONT_SIZE_SMALL = 11            # Маленький текст (таблицы, подписи)
FONT_SIZE_TINY = 9              # Крошечный текст (футер, версии)

# Начертания
FONT_WEIGHT_BOLD = "bold"
FONT_WEIGHT_NORMAL = "normal"


# === СТИЛИ КОМПОНЕНТОВ ===

# Кнопки основные
BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_ACCENT};
        color: {COLOR_BG_PRIMARY};
        font-size: {FONT_SIZE_BODY}px;
        font-weight: {FONT_WEIGHT_BOLD};
        padding: 8px 16px;
        border: none;
        border-radius: 2px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_ACCENT_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_DISABLED};
    }}
"""

# Кнопки маленькие
BUTTON_SMALL_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_ACCENT};
        color: {COLOR_BG_PRIMARY};
        font-size: {FONT_SIZE_SMALL}px;
        font-weight: {FONT_WEIGHT_BOLD};
        padding: 5px 12px;
        border: none;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_ACCENT_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_DISABLED};
    }}
"""

# Кнопки вторичные (тёмные)
BUTTON_SECONDARY_STYLE = f"""
    QPushButton {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL}px;
        padding: 5px 12px;
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_SECONDARY};
        color: {COLOR_TEXT_PRIMARY};
    }}
"""

# Поля ввода (QLineEdit)
LINE_EDIT_STYLE = f"""
    QLineEdit {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: {FONT_SIZE_SMALL}px;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_BORDER};
    }}
    QLineEdit:disabled {{
        background-color: {COLOR_BG_SECONDARY};
        color: {COLOR_TEXT_DISABLED};
    }}
"""

# Таблицы (QTableWidget)
TABLE_STYLE = f"""
    QTableWidget {{
        background-color: {COLOR_BG_SECONDARY};
        color: {COLOR_TEXT_PRIMARY};
        border: none;
        font-size: {FONT_SIZE_SMALL}px;
        outline: none;
    }}
    QHeaderView::section {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_SECONDARY};
        padding: 6px;
        border: 1px solid {COLOR_BORDER};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_SMALL}px;
    }}
    QTableWidget::item {{
        padding: 5px 8px;
        border-bottom: 1px solid {COLOR_BORDER_SUBTLE};
    }}
    QTableWidget::item:selected {{
        background-color: {COLOR_ACCENT};
        color: {COLOR_BG_PRIMARY};
    }}
"""

# Scrollbar
SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: {COLOR_BG_SECONDARY};
        width: 8px;
        border-radius: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLOR_ACCENT};
        border-radius: 6px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_ACCENT_HOVER};
    }}
    QScrollBar::handle:vertical:pressed {{
        background: {COLOR_ACCENT_PRESSED};
    }}
    QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: {COLOR_BG_SECONDARY};
        height: 8px;
        border-radius: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLOR_ACCENT};
        border-radius: 6px;
        min-width: 40px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {COLOR_ACCENT_HOVER};
    }}
    QScrollBar::handle:horizontal:pressed {{
        background: {COLOR_ACCENT_PRESSED};
    }}
    QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
"""

# ComboBox
COMBOBOX_STYLE = f"""
    QComboBox {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_LIGHT};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: {FONT_SIZE_SMALL}px;
        min-width: 100px;
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLOR_BG_TERTIARY};
        color: {COLOR_TEXT_PRIMARY};
        selection-background-color: {ZONE_COLORS['A']};
    }}
"""

# Панели (QFrame)
PANEL_STYLE = f"""
    QFrame {{
        background-color: {COLOR_BG_SECONDARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
    }}
"""

# Заголовки
TITLE_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: {FONT_SIZE_TITLE}px;
        font-weight: {FONT_WEIGHT_BOLD};
        background: transparent;
    }}
"""

HEADING_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: {FONT_SIZE_HEADING}px;
        font-weight: {FONT_WEIGHT_BOLD};
        background: transparent;
    }}
"""

SUBHEADING_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_PRIMARY};
        font-size: {FONT_SIZE_SUBHEADING}px;
        font-weight: {FONT_WEIGHT_BOLD};
        background: transparent;
    }}
"""

# Подписи
LABEL_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: {FONT_SIZE_SMALL}px;
        background: transparent;
    }}
"""

# Футер / версии
FOOTER_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_MUTED};
        font-size: {FONT_SIZE_TINY}px;
        background: transparent;
    }}
"""

# Статус-бар
STATUSBAR_STYLE = f"""
    QStatusBar {{
        background-color: {COLOR_BG_TERTIARY};
        border-top: 1px solid {COLOR_BORDER};
    }}
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: {FONT_SIZE_TINY}px;
    }}
"""

# Прогресс-бар
PROGRESSBAR_STYLE = f"""
    QProgressBar {{
        background-color: {COLOR_BG_SECONDARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        text-align: center;
        color: {COLOR_TEXT_TERTIARY};
        font-size: 9px;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 2px;
    }}
"""

# Иконка статус-бара
STATUSBAR_ICON_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 14px;
        padding: 0px 4px;
    }}
"""

# Чек-боксы (светлый фон, зелёная галочка PNG)
_CHECKBOX_CHECKED_PATH = os.path.join(os.path.dirname(__file__), 'checkbox_checked.png').replace('\\', '/')

CHECKBOX_STYLE = f"""
    QCheckBox {{
        font-size: 11px;
        color: {COLOR_TEXT_PRIMARY};
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 10px;
        height: 10px;
        border-radius: 3px;
    }}
    QCheckBox::indicator:unchecked {{
        background-color: #3A3A3A;
        border: 1.5px solid #5A5A5A;
    }}
    QCheckBox::indicator:checked {{
        background-color: #FFFFFF;
        border: 1.5px solid #FFFFFF;
        image: url({_CHECKBOX_CHECKED_PATH!r});
    }}
    QCheckBox::indicator:hover:unchecked {{
        background-color: #4A4A4A;
        border-color: #7A7A7A;
    }}
    QCheckBox::indicator:hover:checked {{
        background-color: #FFFFFF;
        border-color: #FFFFFF;
    }}
    QCheckBox::indicator:disabled {{
        background-color: #2A2A2A;
        border-color: #444444;
    }}
    QCheckBox:focus {{
        outline: none;
    }}
"""

# Лог-поле (QTextEdit для вывода логов сканирования)
LOG_TEXT_STYLE = f"""
    QTextEdit, QPlainTextEdit {{
        background-color: #0A0A0A;
        color: #CCCCCC;
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 8px;
        font-family: {FONT_FAMILY_MONO};
        font-size: 10px;
        line-height: 1.4;
    }}
"""


# === УТИЛИТЫ ===

def get_zone_style(zone: str) -> str:
    """Получить стиль для зоны ISO 10816."""
    color = ZONE_COLORS.get(zone, ZONE_COLORS['-'])
    return f"""
        QFrame {{
            background-color: {COLOR_BG_TERTIARY};
            border-radius: 8px;
            border: 2px solid {color};
        }}
    """


def get_sensor_status_style(status: str) -> dict:
    """Получить стили для статуса датчика."""
    styles = {
        'empty': {
            'border': COLOR_BG_PRIMARY,
            'fill': COLOR_ACCENT,
            'text': COLOR_BG_PRIMARY,
        },
        'ok': {
            'border': STATUS_COLORS['ok'],
            'fill': COLOR_ACCENT,
            'text': COLOR_BG_PRIMARY,
        },
        'partial': {
            'border': STATUS_COLORS['partial'],
            'fill': COLOR_ACCENT,
            'text': COLOR_BG_PRIMARY,
        },
        'none': {
            'border': STATUS_COLORS['none'],
            'fill': COLOR_ACCENT,
            'text': COLOR_ACCENT,
        },
    }
    return styles.get(status, styles['empty'])


def get_text_style(color: str = COLOR_TEXT_PRIMARY, size: int = FONT_SIZE_BODY, bold: bool = False) -> str:
    """Создать стиль для текста."""
    weight = FONT_WEIGHT_BOLD if bold else FONT_WEIGHT_NORMAL
    return f"""
        color: {color};
        font-size: {size}px;
        font-weight: {weight};
        background: transparent;
    """
