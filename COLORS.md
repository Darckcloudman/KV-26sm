# Справочник цветов интерфейса KWF Prometheus

**Версия:** v1.4 | **Последнее обновление:** 2025-05-20

---

## main_window.py — Главное окно и вкладки

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| QMainWindow | background | `#000000` | 48 |
| central_widget | background | `#000000` | 51 |
| QTabWidget | background | `#000000` | 62 |
| QTabWidget::pane | background | `#000000` | 66 |
| QTabBar::tab (обычная) | background | `#1A1A1A` | 72 |
| QTabBar::tab (обычная) | color | `#888888` | 73 |
| QTabBar::tab (активная) | background | `#000000` | 80 |
| QTabBar::tab (активная) | color | `#FFFFFF` | 81 |
| QTabBar::tab (активная) | border-bottom | `#FFFFFF` (2px) | 82 |
| QTabBar::tab (hover) | background | `#2A2A2A` | 85 |
| QTabBar::tab (hover) | color | `#CCCCCC` | 86 |
| QMenuBar | background | `#000000` | 120 |
| QMenuBar | color | `#FFFFFF` | 121 |
| QMenuBar::item:selected | background | `#333333` | 130 |
| QMenu | background | `#1A1A1A` | 134 |
| QMenu | color | `#FFFFFF` | 135 |
| QMenu::item:selected | background | `#333333` | 139 |
| **QStatusBar** | **background** | **`#2A2A2A`** | **NEW** |
| **QStatusBar** | **border-top** | **`#333333`** | **NEW** |
| **QProgressBar** | **background** | **`#1A1A1A`** | **NEW** |
| **QProgressBar** | **border** | **`#333333`** | **NEW** |
| **QProgressBar::chunk** | **background** | **`#FFFFFF`** | **NEW** |
| **Status icon (ready)** | **qtawesome** | **`mdi.check-circle` `#00C853`** | **NEW** |
| **Status icon (loading)** | **qtawesome** | **`mdi.loading` `#FFC107`** | **NEW** |
| **Status icon (error)** | **qtawesome** | **`mdi.alert-circle` `#DD2C00`** | **NEW** |
| **Status icon (DB mode)** | **qtawesome** | **`mdi.database` `#448AFF`** | **NEW** |
| **Status icon (file mode)** | **qtawesome** | **`mdi.folder` `#888888`** | **NEW** |

---

## home_screen.py — Экран Home

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| HomeScreen (QPalette.Window) | background | `#000000` | 422 |
| Заголовок "KWF Prometheus" | color | `#FFFFFF` | 432 |
| Кнопки (QPushButton) | background | `#FFFFFF` | 445 |
| Кнопки (QPushButton) | color | `#000000` | 446 |
| Кнопки (hover) | background | `#E8E8E8` | 454 |
| Кнопки (pressed) | background | `#D0D0D0` | 455 |
| path_label | color | `#ffffff` | 469 |
| table_frame (QFrame) | background | `#ff0000` | 484 |
| QTableWidget | background | `#1A1A1A` | 499 |
| QTableWidget | color | `#FFFFFF` | 500 |
| QHeaderView::section | background | `#2A2A2A` | 507 |
| QHeaderView::section | color | `#AAAAAA` | 508 |
| QHeaderView::section | border | `#333333` | 510 |
| QTableWidget::item | border-bottom | `#2A2A2A` | 516 |
| QTableWidget::item:selected | background | `#FFFFFF` | 519 |
| QTableWidget::item:selected | color | `#000000` | 520 |
| QScrollBar (vertical) | background | `#1A1A1A` | 523 |
| QScrollBar::handle (vertical) | background | `#E0E0E0` | 528 |
| QScrollBar::handle:hover | background | `#FFFFFF` | 533 |
| QScrollBar::handle:pressed | background | `#B0B0B0` | 536 |
| status_frame (QFrame) | background | `#000000` | 581 |
| Номер датчика (num_label) | color | `#FFFFFF` | 593 |
| Описание датчика (desc_label) | color | `#BBBBBB` | 597 |
| Статус "[нет данных]" | color | `#F44336` | 601 |
| Статус "[ok]" | color | `#4CAF50` | 879 |
| Статус "[частично]" | color | `#FFC107` | 882 |
| Статус пустой | color | `#444444` | 888 |
| Выделенный датчик | background | `#333333` | 894 |
| Кнопка "Проанализировать" | background | `#FFFFFF` | 613 |
| Кнопка "Проанализировать" (disabled) | background | `#333333` | 622 |
| Кнопка "Проанализировать" (disabled) | color | `#666666` | 622 |
| version_label | color | `#444444` | 630 |
| mode_label | color | `#555555` | 638 |
| LoadingSpinner лучи | цвет | `#888888` (с прозрачностью) | 98 |
| Индикатор датчика `empty` | border | `#000000` | 274 |
| Индикатор датчика `empty` | text | `#000000` | 276 |
| Индикатор датчика `ok` | border (пульс) | `#4CAF50` → `#1a4a1a` | 278-280 |
| Индикатор датчика `ok` | text | `#000000` | 282 |
| Индикатор датчика `partial` | border (пульс) | `#FFC107` → `#4a3a00` | 284-286 |
| Индикатор датчика `partial` | text | `#000000` | 288 |
| Индикатор датчика `none` | border | `#F44336` | 290 |
| Индикатор датчика `none` | fill | `#FFFFFF` | 291 |
| Индикатор датчика `none` | text | `#FFFFFF` | 292 |
| Выделение датчика (selected) | border | `#FFFFFF` | 305 |

---

## analysis_data_screen.py — Анализ данных

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| AnalysisDataScreen | background | `#000000` | 85 |
| ZoneIndicator | background | `#2D2D2D` | 34, 71 |
| ZoneIndicator | border | `#424242` | 36 |
| ZoneIndicator (зона A) | border/text | `#00C853` | 22 |
| ZoneIndicator (зона B) | border/text | `#FFD600` | 23 |
| ZoneIndicator (зона C) | border/text | `#FF6D00` | 24 |
| ZoneIndicator (зона D) | border/text | `#DD2C00` | 25 |
| ZoneIndicator (нет данных) | border/text | `#424242` | 26 |
| ZoneIndicator title | color | `#B0B0B0` | 44 |
| ZoneIndicator zone_label | color | `#FFFFFF` | 48 |
| ZoneIndicator rms_label | color | `#888888` | 52 |
| Метки "Датчик:", "Зоны ISO 10816" | color | `#FFFFFF` | 112, 140 |
| QComboBox | background | `#2D2D2D` | 116 |
| QComboBox | color | `#FFFFFF` | 117 |
| QComboBox | border | `#424242` | 118 |
| QComboBox (выпадающий список) | background | `#2D2D2D` | 125 |
| QComboBox (выделение) | background | `#00C853` | 127 |
| Заголовки "Временные ряды", "Спектры" | color | `#FFFFFF` | 160, 173 |

---

## metric_card.py — Карточки метрик

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| MetricCard | background | `#1A1A1A` | 97 |
| MetricCard | border | `#333333` | 98 |
| Заголовок (title_label) | color | `#AAAAAA` | 111 |
| Значение (value_label) | color | `#FFFFFF` | 125 |
| Единица (unit_label) | color | `#888888` | 136 |
| CircularProgressBar фон | color | `#444444` | 46 |
| CircularProgressBar текст | color | `#FFFFFF` | 65 |
| Progress < 70% | color | `#00C853` | 172 |
| Progress 70-90% | color | `#FFD600` | 174 |
| Progress > 90% | color | `#D50000` | 176 |

---

## charts/time_series_chart.py — Временные ряды

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| pyqtgraph background | background | `#000000` | 30 |
| pyqtgraph foreground | foreground | `#FFFFFF` | 31 |
| Заголовок графика | color | `#FFFFFF` | 34 |
| Подписи осей | color | `#AAAAAA` | 35-36 |
| Текст на осях | color | `#888888` | 43-44 |
| Линии сетки/делений | color | `#444444` | 45-46 |
| Линия графика | color | `#FFFFFF` | 52 |

---

## charts/spectrum_chart.py — Спектры

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| pyqtgraph background | background | `#000000` | 34 |
| pyqtgraph foreground | foreground | `#FFFFFF` | 35 |
| Заголовок | color | `#FFFFFF` | 38 |
| Подписи осей | color | `#AAAAAA` | 39-40 |
| Текст на осях | color | `#888888` | 47-48 |
| Линии сетки | color | `#444444` | 49-50 |
| Линия спектра | color | `#FFFFFF` | 55 |
| Подсветка пиков | brush | `QColor(0, 200, 83, 30)` | 107 |

---

## canvas.py — Canvas (старый компонент)

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| Фон | background | `#000000` | 18, 63 |
| Текст "Нет данных" | color | `#666666` | 66 |
| Оси | color | `#333333` | 82 |
| Подписи осей | color | `#a0a0a0` | 87 |
| Границы зон A/B, B/C, C/D | color | `#555555`, `#666666`, `#777777` | 94 |
| Метки зон | color | `#888888` | 100 |
| Спектр | color | `#ff69b4` | 105 |
| Заголовок | color | `#e0e0e0` | 111 |
| Метки частот | color | `#666666` | 116 |

---

## raw_data_screen.py — Сырые данные

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| Фон виджета | background | `#1a1a1a` | 25 |
| Фон отрисовки | background | `#1a1a1a` | 47 |
| Текст "Нет данных" | color | `#666666` | 50 |
| Сигнал | color | `#ff69b4` | 77 |
| Заголовок датчика | color | `#ff69b4` | 83 |
| Подписи осей | color | `#888888` | 88 |
| Заголовок экрана | color | `#ff69b4` | 107 |
| ScrollArea | background | `#0a0a0a` | 112 |
| Панель датчика (QFrame) | background | `#1a1a1a` | 125 |
| Панель датчика | border | `#333333` | 125 |
| Заголовок панели | color | `#ff69b4` | 131 |
| Заголовок панели | background | `#0a0a0a` | 131 |

---

## upload_info_screen.py — Информация о загрузке

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| Заголовок "[=] ИНФОРМАЦИЯ" | color | `#ff69b4` | 54 |
| Заголовок | border-bottom | `#333333` | 56 |
| Информация о ВЭУ | color | `#e0e0e0` | 64 |
| Информация о ВЭУ | background | `#1a1a1a` | 66 |
| Параметры записи | color | `#ffa500` | 75 |
| Параметры записи | background | `#0a0a0a` | 77 |
| Параметры записи | border | `#333333` | 78 |
| Счётчик (все загружены) | color | `#00ff00` | 205 |
| Счётчик (неполный) | color | `#ffa500` | 215, 226 |
| ScrollArea | background | `#0a0a0a` | 100 |
| ScrollArea | border | `#333333` | 99 |
| Панель датчика (QFrame) | background | `#1a1a1a` | 241 |
| Панель датчика | border | `#333333` | 242 |
| Статус [OK] | color | `#00ff00` | 258 |
| Статус [~] | color | `#ffa500` | 265 |
| Статус [-] | color | `#ff0000` | 268 |
| Описание датчика | color | `#e0e0e0` | 277 |

---

## directory_tree_dialog.py — Диалог выбора каталога (Tree View)

| Элемент | Свойство | Цвет / Значение | Строка |
|---------|----------|-----------------|--------|
| QDialog | background | `#1A1A1A` | 99 |
| QDialog | fixed-size | `480×530 px` | — |
| QTreeView | background | `#1A1A1A` | 102 |
| QTreeView | color | `#FFFFFF` | 103 |
| QTreeView | border | `#333333` | 104 |
| QTreeView | font-size | `10px` | 106 |
| QTreeView | icon-size | `8×8 px` | — |
| QTreeView::item | color | `#FFFFFF` | 111 |
| QTreeView::item | padding | `0px 4px` | 111 |
| QTreeView::item | min-height | `14px` | 111 |
| QTreeView::item | border-bottom | `rgba(255,255,255,0.03)` | 111 |
| QTreeView::item:selected | background | `#333333` | 115 |
| QTreeView::item:hover | background | `#2A2A2A` | 119 |
| **QTreeView::branch (линии связей)** | **border-left** | **`rgba(255,255,255,0.28)` пунктир** | 124–148 |
| **QTreeView::branch (линии связей)** | **border-bottom** | **`rgba(255,255,255,0.28)` пунктир** | 124–148 |
| QHeaderView::section | background | `#2A2A2A` | 150 |
| QHeaderView::section | color | `#FFFFFF` | 151 |
| QHeaderView::section | border-bottom | `#333333` | 154 |
| QPushButton (основные) | background | `#FFFFFF` | 159 |
| QPushButton (основные) | color | `#000000` | 160 |
| QPushButton (основные) | border-radius | `6px` | 161 |
| QPushButton:hover | background | `#E8E8E8` | 166 |
| QPushButton:pressed | background | `#D0D0D0` | 169 |
| **Кнопки навигации [nav="true"]** | **background** | **`#2D2D2D`** | 172 |
| **Кнопки навигации [nav="true"]** | **color** | **`#FFFFFF`** | 173 |
| **Кнопки навигации [nav="true"]** | **border-radius** | **`4px`** | 174 |
| **Кнопки навигации [nav="true"]** | **min/max width** | **`28px`** | 177 |
| **Кнопки навигации [nav="true"]** | **min/max height** | **`28px`** | 178 |
| Кнопки навигации:hover | background | `#3D3D3D` | 181 |
| Кнопки навигации:pressed | background | `#4D4D4D` | 184 |
| **Кнопки навигации:disabled** | **background** | **`#252525`** | 187 |
| **Кнопки навигации:disabled** | **color** | **`#555555`** | 188 |
| QLineEdit (Path) | background | `#2A2A2A` | — |
| QLineEdit (Path) | color | `#FFFFFF` | — |
| QLineEdit (Path) | border | `#3A3A3A` | — |
| QLabel (path label) | color | `#AAAAAA` | 78 |
| **QScrollBar (custom)** | background | `#1A1A1A` | — |
| **QScrollBar::handle** | background | `#E0E0E0` | — |
| **QScrollBar::handle:hover** | background | `#FFFFFF` | — |
| **styled_message_box (все типы)** | **background** | **`#5A5A5A`** | — |
| **styled_message_box QLabel** | **color** | **`#FFFFFF`** | — |
| **styled_message_box QPushButton** | **background** | **`#FFFFFF`** | — |
| **styled_message_box QPushButton** | **color** | **`#000000`** | — |
| **Alert icon (critical)** | **qtawesome** | **`mdi.alert` `#FF5252`** | — |
| **Alert icon (warning)** | **qtawesome** | **`mdi.alert` `#FFC107`** | — |
| **Info icon** | **qtawesome** | **`mdi.information` `#448AFF`** | — |
| **Question icon** | **qtawesome** | **`mdi.help-circle` `#448AFF`** | — |

---

## settings_dialog.py — Настройки

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| QDialog | background | `#000000` | NEW |
| QTabWidget::pane | background | `#1A1A1A` | NEW |
| QTabWidget::pane | border | `#333333` | NEW |
| QTabBar::tab | background | `#2A2A2A` | NEW |
| QTabBar::tab | color | `#888888` | NEW |
| QTabBar::tab:selected | background | `#1A1A1A` | NEW |
| QTabBar::tab:selected | color | `#FFFFFF` | NEW |
| QTabBar::tab:selected | border-bottom | `#FFFFFF` | NEW |
| QLineEdit | background | `#2A2A2A` | NEW |
| QLineEdit | color | `#FFFFFF` | NEW |
| QLineEdit | border | `#333333` | NEW |
| QSpinBox | background | `#2A2A2A` | NEW |
| QSpinBox | color | `#FFFFFF` | NEW |
| QSpinBox | border | `#333333` | NEW |
| QComboBox | background | `#2A2A2A` | NEW |
| QComboBox | color | `#FFFFFF` | NEW |
| QComboBox | border | `#333333` | NEW |
| QCheckBox | color | `#FFFFFF` | NEW |
| ModuleStatusIndicator | background | `#2A2A2A` | NEW |
| ModuleStatusIndicator | border | `#333333` | NEW |
| Status dot (OK) | background | `#00C853` | NEW |
| Status dot (error) | background | `#DD2C00` | NEW |
| Критичный модуль label | color | `#DD2C00` | NEW |

## trends_screen.py — Тренды

| Элемент | Свойство | Цвет | Строка |
|---------|----------|------|--------|
| QWidget | background | `#000000` | NEW |
| QFrame (control_panel) | background | `#1A1A1A` | NEW |
| QFrame (control_panel) | border | `#333333` | NEW |
| QComboBox | background | `#000000` | NEW |
| QComboBox | color | `#FFFFFF` | NEW |
| QComboBox | border | `#333333` | NEW |
| QCheckBox | color | `#BBBBBB` | NEW |
| pyqtgraph background | background | `#000000` | NEW |
| pyqtgraph foreground | foreground | `#FFFFFF` | NEW |
| График линия | color | `#FFFFFF` | NEW |
| График точки | color | `#FFFFFF` | NEW |
| Порог A | color | `#00C853` (dash) | NEW |
| Порог B | color | `#FFC107` (dash) | NEW |
| Порог C | color | `#FF9800` (dash) | NEW |
| QFrame (stats_panel) | background | `#1A1A1A` | NEW |
| QFrame (stats_panel) | border | `#333333` | NEW |

---

## vibration_analysis.py — Зоны вибрации

| Зона | Цвет |
|------|------|
| A (Хорошо) | `#00C853` |
| B (Удовлетворительно) | `#FFD600` |
| C (Неудовлетворительно) | `#FFAB00` |
| D (Критично) | `#D50000` |
| Нет данных | `#FFFFFF` |

---

## Правила обновления

1. При изменении любого цвета — обновить эту таблицу
2. При добавлении нового элемента — добавить строку в соответствующий раздел
3. При удалении элемента — удалить строку из таблицы
4. Нумерация строк актуальна на момент последнего обновления
