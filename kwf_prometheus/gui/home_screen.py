# -*- coding: utf-8 -*-
"""
Вкладка Home (home_screen.py)
==============================
Главный экран приложения KWF Prometheus.

Содержит:
- Таблицу архивов с поиском
- Схему расположения датчиков
- Индикаторы статуса
- Кнопки загрузки
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QProgressBar, QAbstractItemView, QTreeView,
    QDialog, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QRect, QVariantAnimation, QEasingCurve, QAbstractAnimation, QTimer, QPropertyAnimation
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPixmap, QPalette, QConicalGradient


class LoadingSpinner(QWidget):
    """Крутящийся индикатор загрузки для ячейки таблицы."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self._angle = 0
        self._is_spinning = False
        
        # Анимация вращения через QVariantAnimation
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(1000)  # 1 секунда на оборот (плавнее)
        self._animation.setStartValue(0)
        self._animation.setEndValue(360)
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)  # Плавное линейное вращение
        self._animation.setLoopCount(-1)  # Бесконечно
        self._animation.valueChanged.connect(self._on_angle_changed)
        
    def _on_angle_changed(self, value):
        """Обработчик изменения угла анимации."""
        self._angle = int(value) % 360
        self.update()

    def start(self):
        """Запустить анимацию."""
        self._is_spinning = True
        self.show()
        self._animation.start()

    def stop(self):
        """Остановить анимацию."""
        self._is_spinning = False
        self._animation.stop()
        self.hide()
        self._angle = 0
        self.update()

    def paintEvent(self, event):
        """Отрисовка крутящегося индикатора."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self._is_spinning:
            return

        # Центр и радиус
        cx, cy = self.width() // 2, self.height() // 2
        radius = 10
        
        # Градиент для сегментов
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        
        # Рисуем 8 сегментов с разной прозрачностью (серый градиент)
        for i in range(8):
            painter.rotate(45)
            alpha = int(255 * (i + 1) / 8)
            # Серый цвет #888888 с градиентной прозрачностью
            painter.setPen(QPen(QColor(136, 136, 136, alpha), 2))
            painter.drawLine(0, -radius, 0, -radius + 3)  # Лучи в 2 раза короче (3px)
        
        painter.resetTransform()

class PulseRedDot(QWidget):
    """Пульсирующая красная точка — индикатор точки подключения.

    Кружок растёт из центра (диаметр 2→8 px) и плавно исчезает.
    Анимация бесконечная, запускается автоматически при создании.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self._progress = 0.0

        self._animation = QPropertyAnimation(self, b"progress")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.start()

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float):
        self._progress = value
        self.update()

    progress = property(get_progress, set_progress)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        min_radius = 1.0   # диаметр 2 px
        max_radius = 4.0   # диаметр 8 px
        current_radius = min_radius + (max_radius - min_radius) * self._progress
        opacity = 1.0 - self._progress

        center = QPointF(self.width() / 2, self.height() / 2)
        painter.setOpacity(opacity)
        painter.setBrush(QBrush(QColor(255, 59, 59)))   # ярко-красный
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, current_radius, current_radius)


from ..parsers.rd2_parser import MultiSensorRD2Parser, RD2Parser
from ..dal.repositories.base import IVibrationRepository
from ..dal.logger import get_logger
from ..app_settings import get_last_archive_dir, set_last_archive_dir
from .directory_tree_dialog import DirectoryTreeDialog
from .archive_tree_dialog import ArchiveTreeDialog
from .rd2_tree_dialog import Rd2TreeDialog
from .styled_message_box import show_critical, show_warning, show_info
from .ui_styles import CHECKBOX_STYLE

logger = get_logger("HomeScreen")


SENSOR_DESCRIPTIONS = [
    "Главный вал, радиальное направление",
    "Передняя нижняя часть редуктора",
    "Средняя нижняя часть редуктора",
    "Выход трансмиссии, радиальное направление",
    "Выход трансмиссии, осевое направление",
    "Подшипник генератора со стороны ротора, осевое направление",
    "Подшипник генератора со стороны ротора, радиальное направление",
    "Подшипник генератора, осевое направление",
]

# Координаты датчиков на shema.png — подогнаны вручную и зафиксированы.
# Изменять только при замене изображения shema.png!
SENSOR_POSITIONS = [
    (0.102, 0.698),   # 1 - нижний левый
    (0.472, 0.918),   # 2 - нижний центр-лево
    (0.505, 0.647),   # 3 - нижний центр
    (0.894, 0.87),    # 4 - правый нижний
    (0.833, 0.62),    # 5 - правый средний
    (0.182, 0.32),    # 6 - верхний левый
    (0.047, 0.304),   # 7 - верхний центр
    (0.881, 0.378),   # 8 - верхний правый (отдельный круг)
]

# Координаты точек подключения на shema.png — относительные (0.0–1.0).
# Чтобы подстроить положение: открой shema.png в любом редакторе,
# определи x и y в пикселях от левого верхнего угла, раздели на
# ширину/высоту изображения. Пример: для shema.png 2564×1612 px
# точка в (500, 400) → (500/2564, 400/1612) ≈ (0.195, 0.248)
CONNECTION_POSITIONS = [
    (0.120, 0.720),   # 1 — точка подключения датчика 1
    (0.490, 0.940),   # 2
    (0.520, 0.670),   # 3
    (0.910, 0.890),   # 4
    (0.850, 0.640),   # 5
    (0.200, 0.340),   # 6
    (0.065, 0.324),   # 7
    (0.898, 0.398),   # 8
]


class ParseThread(QThread):
    """Поток для загрузки архива через репозиторий.
    
    Использует asyncio.new_event_loop() вместо asyncio.run()
    для избежания конфликтов с PyQt event loop.
    """
    finished = Signal(bool, str, object)
    error = Signal(str)
    progress = Signal(int)  # Сигнал прогресса (0-100)
    load_result = Signal(object)  # Dict с результатами загрузки (added, skipped, errors)

    def __init__(self, file_path: str, repository: IVibrationRepository, persistence_service=None):
        super().__init__()
        self.file_path = file_path
        self.repository = repository
        self.persistence_service = persistence_service
        self._is_cancelled = False

    def cancel(self):
        """Отменить загрузку."""
        self._is_cancelled = True

    def run(self):
        """Запустить загрузку через репозиторий."""
        import asyncio
        try:
            # Создаём новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Прогресс: начало загрузки (25%)
                if not self._is_cancelled:
                    self.progress.emit(25)
                
                # Если есть persistence_service — используем его (v1.4+)
                if self.persistence_service is not None:
                    load_result = loop.run_until_complete(
                        self.persistence_service.save_archive(Path(self.file_path))
                    )
                else:
                    # Fallback: используем репозиторий напрямую
                    load_result = loop.run_until_complete(
                        self.repository.load_archive(Path(self.file_path))
                    )

                if self._is_cancelled:
                    return
                
                # Отправляем результаты загрузки
                self.load_result.emit(load_result)
                
                # Прогресс: загрузка завершена (50%)
                if load_result.get('success', False):
                    self.progress.emit(50)
                    
                    # Получаем парсер для обратной совместимости
                    parser = loop.run_until_complete(
                        self.repository.get_archive_parser(self.file_path)
                    )
                    
                    if self._is_cancelled:
                        return
                    
                    # Прогресс: парсер готов (100%)
                    self.progress.emit(100)
                    self.finished.emit(True, self.file_path, parser)
                else:
                    self.progress.emit(0)
                    self.finished.emit(False, self.file_path, None)
            finally:
                loop.close()
                
        except Exception as e:
            self.progress.emit(0)
            self.error.emit(str(e))


class SensorIndicator(QWidget):
    """Круглый индикатор датчика с плавным миганием."""
    clicked = Signal(int)

    def __init__(self, sensor_id, parent=None):
        super().__init__(parent)
        self.sensor_id = sensor_id
        self.status = 'empty'
        self.selected = False
        self._glow = 1.0
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(1200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.valueChanged.connect(self._on_glow_changed)
        self._animation.finished.connect(self._on_animation_finished)

    def _on_glow_changed(self, value):
        self._glow = value
        self.update()

    def _on_animation_finished(self):
        if self._animation.direction() == QAbstractAnimation.Direction.Forward:
            self._animation.setDirection(QAbstractAnimation.Direction.Backward)
        else:
            self._animation.setDirection(QAbstractAnimation.Direction.Forward)
        self._animation.start()

    @staticmethod
    def _lerp_color(c1, c2, t):
        return QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
        )

    def setStatus(self, status):
        """Установить статус индикатора и управлять анимацией мигания.

        Мигание запускается только для 'ok' и 'partial' (плавный glow).
        Для 'empty' и 'none' анимация останавливается — рамка статична.
        """
        self.status = status
        if status in ('ok', 'partial'):
            if self._animation.state() != QAbstractAnimation.State.Running:
                self._animation.start()
        else:
            self._animation.stop()
            self._glow = 1.0
        self.update()

    def setSelected(self, selected):
        self.selected = selected
        self.update()

    def paintEvent(self, event):
        """Отрисовка кружка индикатора.

        Логика отображения по статусам:
          empty   → чёрная рамка, белый центр, чёрный номер
          ok      → зелёная пульсирующая рамка, белый центр, чёрный номер
          partial → жёлтая пульсирующая рамка, белый центр, чёрный номер
          none    → красная рамка, белый центр, белый номер
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 11
        cx, cy = 13, 13

        if self.status == 'empty':
            border_color = QColor("#000000")
            fill_brush = QBrush(QColor("#FFFFFF"))
            text_color = QColor("#000000")
        elif self.status == 'ok':
            bright = QColor("#4CAF50")
            dark = QColor("#1a4a1a")
            border_color = self._lerp_color(dark, bright, self._glow)
            fill_brush = QBrush(QColor("#FFFFFF"))
            text_color = QColor("#000000")
        elif self.status == 'partial':
            bright = QColor("#FFC107")
            dark = QColor("#4a3a00")
            border_color = self._lerp_color(dark, bright, self._glow)
            fill_brush = QBrush(QColor("#FFFFFF"))
            text_color = QColor("#000000")
        else:
            border_color = QColor("#F44336")
            fill_brush = QBrush(QColor("#FFFFFF"))
            text_color = QColor("#FFFFFF")

        painter.setBrush(fill_brush)
        painter.setPen(QPen(border_color, 5))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.setPen(QPen(text_color))
        font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRect(cx - r, cy - r, r * 2, r * 2)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(self.sensor_id))

        if self.selected:
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - r - 2, cy - r - 2, (r + 2) * 2, (r + 2) * 2)

    def mousePressEvent(self, event):
        self.clicked.emit(self.sensor_id)


class SensorScheme(QFrame):
    """Схема турбины с shema.png и индикаторами."""
    sensor_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(900, 600)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #000000; border: none;")

        self._pixmap = None
        self._scaled_pixmap = None
        self._indicators = []
        self._connection_dots = []
        self._pixmap_x = 0
        self._pixmap_y = 0
        self._scale = 1.0

        # Загрузка shema.png
        possible_paths = [
            Path(__file__).resolve().parent.parent.parent.parent / "img" / "shema.png",
            Path("img/shema.png"),
            Path("../img/shema.png"),
        ]
        for p in possible_paths:
            if p.exists():
                self._pixmap = QPixmap(str(p))
                break

        # Создаём индикаторы датчиков
        for i in range(8):
            indicator = SensorIndicator(i + 1, self)
            indicator.clicked.connect(self.sensor_clicked.emit)
            self._indicators.append(indicator)
            indicator.show()

        # Создаём точки подключения (пульсирующие красные кружки)
        for _ in range(8):
            dot = PulseRedDot(self)
            self._connection_dots.append(dot)
            dot.show()

    def set_sensor_status(self, sensor_id, status):
        if 1 <= sensor_id <= 8:
            self._indicators[sensor_id - 1].setStatus(status)

    def set_selected_sensor(self, sensor_id):
        for i, ind in enumerate(self._indicators):
            ind.setSelected(i + 1 == sensor_id)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_layout()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_layout()

    def _update_layout(self):
        if not self._pixmap or self._pixmap.isNull():
            return

        w, h = self.width(), self.height()
        self._scaled_pixmap = self._pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._pixmap_x = (w - self._scaled_pixmap.width()) // 2
        self._pixmap_y = (h - self._scaled_pixmap.height()) // 2
        self._scale = self._scaled_pixmap.width() / self._pixmap.width()

        for i, (rel_x, rel_y) in enumerate(SENSOR_POSITIONS):
            ind = self._indicators[i]
            x = self._pixmap_x + int(rel_x * self._pixmap.width() * self._scale) - 13
            y = self._pixmap_y + int(rel_y * self._pixmap.height() * self._scale) - 13
            ind.move(x, y)

        # Позиционируем точки подключения (центр точки = координата)
        for i, (rel_x, rel_y) in enumerate(CONNECTION_POSITIONS):
            dot = self._connection_dots[i]
            x = self._pixmap_x + int(rel_x * self._pixmap.width() * self._scale) - 15
            y = self._pixmap_y + int(rel_y * self._pixmap.height() * self._scale) - 15
            dot.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self._scaled_pixmap and not self._scaled_pixmap.isNull():
            painter.drawPixmap(self._pixmap_x, self._pixmap_y, self._scaled_pixmap)


class HomeScreen(QWidget):
    """Вкладка Home."""
    analyze_requested = Signal(object)

    def __init__(self, repository: IVibrationRepository, persistence_service=None, auto_scan_service=None, parent=None):
        """
        Инициализация HomeScreen.

        Args:
            repository: Репозиторий для доступа к данным.
            persistence_service: Сервис сохранения данных (v1.4+).
            auto_scan_service: Сервис автопарсинга (v1.4+).
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self.repository = repository
        self.persistence_service = persistence_service
        self.auto_scan_service = auto_scan_service
        self.parser = None
        self.current_file = None
        
        # Загружаем последнюю выбранную папку или используем test_data по умолчанию
        last_dir = get_last_archive_dir()
        if last_dir:
            self.archive_dir = last_dir
        else:
            self.archive_dir = Path(__file__).resolve().parent.parent.parent / "test_data"
        
        self._all_archives = []  # Все архивы для фильтрации
        self._setup_ui()
        self._scan_archives()

        # Индикатор загрузки (прогресс-бар)
        self._loading_spinner = None
        self._loading_row = -1
        self._is_loading = False

        # Запускаем автопарсинг если доступен
        if self.auto_scan_service is not None:
            self.auto_scan_service.start_timer(self)

    def _setup_ui(self):
        # Чёрный фон через палитру
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 20, 60, 15)
        main_layout.setSpacing(14)

        # Заголовок
        title = QLabel("KWF Prometheus")
        title.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Основной контент: левая колонка (кнопки + таблица) | правая колонка (схема + статусы)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # --- Левая колонка ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        btn_style = """
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                font-size: 12px;
                padding: 7px 16px;
                border: none;
                border-radius: 2px;
                min-width: 190px;
                text-align: left;
            }
            QPushButton:hover { background-color: #E8E8E8; }
            QPushButton:pressed { background-color: #D0D0D0; }
        """

        self.load_rd2_btn = QPushButton("Загрузить файл .rd2")
        self.load_rd2_btn.setStyleSheet(btn_style)
        self.load_rd2_btn.clicked.connect(self._load_rd2_file)
        left_layout.addWidget(self.load_rd2_btn)

        self.load_btn = QPushButton("Загрузить архив .zip")
        self.load_btn.setStyleSheet(btn_style)
        self.load_btn.clicked.connect(self._load_archive)
        left_layout.addWidget(self.load_btn)

        self.dir_btn = QPushButton("Выбрать место хранения архивов")
        self.dir_btn.setStyleSheet(btn_style)
        self.dir_btn.clicked.connect(self._select_directory)
        left_layout.addWidget(self.dir_btn)

        # --- Автопарсинг (v1.4) ---
        self.auto_scan_checkbox = QCheckBox("Автоматически импортировать новые архивы")
        self.auto_scan_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.auto_scan_checkbox.setChecked(self.auto_scan_service is not None and self.auto_scan_service.enabled)
        self.auto_scan_checkbox.stateChanged.connect(self._on_auto_scan_toggled)
        left_layout.addWidget(self.auto_scan_checkbox)
        # --- Конец автопарсинга ---

        # Таблица
        table_frame = QFrame()
        table_frame.setStyleSheet("QFrame { background-color: #ff0000; border: 1px solid #333333; border-radius: 4px; }")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)

        # Поле поиска
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #666666;
            }
        """)
        self.search_input.textChanged.connect(self._filter_archives)
        search_layout.addWidget(self.search_input)
        
        self.search_clear_btn = QPushButton("Очистить")
        self.search_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #AAAAAA;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #444444; color: #FFFFFF; }
        """)
        self.search_clear_btn.setFixedWidth(70)
        self.search_clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(self.search_clear_btn)
        table_layout.addLayout(search_layout)

        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(3)  # WTG, Дата, Размер
        self.archive_table.setHorizontalHeaderLabels(["WTG", "Дата записи", "Размер"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.archive_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.archive_table.setMinimumWidth(300)
        self.archive_table.setMaximumWidth(600)
        self.archive_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: none;
                font-size: 11px;
                outline: none;
                margin-left: 8px;
            }
            QHeaderView::section {
                background-color: #2A2A2A;
                color: #AAAAAA;
                padding: 6px;
                border: 1px solid #333333;
                font-weight: bold;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #2A2A2A;
            }
            QTableWidget::item:selected {
                background-color: #FFFFFF;
                color: #000000;
            }
            QScrollBar:vertical {
                background: #1A1A1A;
                width: 8px;
                border-radius: 8px;
            }
            QScrollBar::handle:vertical {
                background: #E0E0E0;
                border-radius: 6px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #FFFFFF;
            }
            QScrollBar::handle:vertical:pressed {
                background: #B0B0B0;
            }
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #1A1A1A;
                height: 8px;
                border-radius: 8px;
            }
            QScrollBar::handle:horizontal {
                background: #E0E0E0;
                border-radius: 6px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #FFFFFF;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #B0B0B0;
            }
            QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        self.archive_table.itemSelectionChanged.connect(self._on_archive_selected)
        table_layout.addWidget(self.archive_table)

        left_layout.addWidget(table_frame, 1)
        content_layout.addWidget(left_panel, 0)

        # --- Правая колонка: схема + статусы ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Схема
        scheme_wrapper = QHBoxLayout()
        self.scheme = SensorScheme()
        self.scheme.sensor_clicked.connect(self._on_sensor_clicked)
        scheme_wrapper.addWidget(self.scheme, alignment=Qt.AlignmentFlag.AlignTop)
        scheme_wrapper.addStretch()
        right_layout.addLayout(scheme_wrapper, 0)

        # Список статусов
        status_wrapper = QHBoxLayout()
        status_frame = QFrame()
        status_frame.setStyleSheet("QFrame { background-color: #000000; border: 0px; border-radius: 0px; }")
        status_layout = QGridLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setHorizontalSpacing(8)
        status_layout.setVerticalSpacing(4)
        status_layout.setColumnStretch(1, 1)
        status_layout.setColumnStretch(2, 0)

        self.status_labels = {}
        for i, desc in enumerate(SENSOR_DESCRIPTIONS):
            sensor_id = i + 1

            num_label = QLabel(f"{sensor_id}.")
            num_label.setStyleSheet("color: #FFFFFF; font-size: 11px; background: transparent; min-width: 18px;")
            status_layout.addWidget(num_label, i, 0, alignment=Qt.AlignmentFlag.AlignTop)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #BBBBBB; font-size: 11px; background: transparent;")
            status_layout.addWidget(desc_label, i, 1, alignment=Qt.AlignmentFlag.AlignTop)

            status_label = QLabel("[нет данных]")
            status_label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold; background: transparent;")
            status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_layout.addWidget(status_label, i, 2, alignment=Qt.AlignmentFlag.AlignTop)

            self.status_labels[sensor_id] = status_label

        status_frame.setMaximumWidth(650)
        status_wrapper.addWidget(status_frame)
        status_wrapper.addStretch()
        
        status_container = QWidget()
        status_container.setLayout(status_wrapper)
        right_layout.addWidget(status_container, 0, Qt.AlignmentFlag.AlignTop)
        # Убрали addStretch() — панель минимальной высоты

        content_layout.addWidget(right_panel, 1, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(content_layout, 2)

        # Кнопка анализа
        self.analyze_btn = QPushButton("Проанализировать")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                font-size: 12px;
                padding: 8px 32px;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
            QPushButton:pressed { background-color: #D0D0D0; }
            QPushButton:disabled { background-color: #333333; color: #666666; }
        """)
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._analyze)
        main_layout.addWidget(self.analyze_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Версия и режим работы
        version_label = QLabel("v1.4.1 | A.Telezhenko, 2026")
        version_label.setStyleSheet("color: #444444; font-size: 9px; background: transparent;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(version_label)

        # Индикатор режима хранения (добавлено в v1.3)
        from ..dal.config import settings
        mode_text = "PostgreSQL" if settings.use_database else "Файловая система"
        mode_label = QLabel(f"Режим хранения данных: {mode_text}")
        mode_label.setStyleSheet("color: #555555; font-size: 9px; background: transparent;")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(mode_label)

    def set_repository(self, repository):
        """Установить новый репозиторий (при динамическом переключении)."""
        self.repository = repository
        
    def _select_directory(self):
        """Выбрать каталог с архивами и сохранить путь."""
        try:
            dialog = DirectoryTreeDialog(self, str(self.archive_dir))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_dir = dialog.get_selected_directory()
                if selected_dir:
                    self.archive_dir = Path(selected_dir)
                    set_last_archive_dir(self.archive_dir)
                    self._scan_archives()
        except Exception as e:
            show_critical(
                self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}"
            )
            
    def add_archives(self, archives: list):
        """Добавить архивы в таблицу (из сканирования настроек).
        
        Args:
            archives: Список словарей с ключами turbine, date_str, size, path, filename
        """
        if not archives:
            return

        # Добавляем новые архивы, избегая дубликатов по пути
        existing_paths = {a['path'] for a in self._all_archives}
        added_count = 0
        
        for archive in archives:
            if archive['path'] not in existing_paths:
                self._all_archives.append(archive)
                existing_paths.add(archive['path'])
                added_count += 1
        
        # Сортируем по имени файла
        self._all_archives.sort(key=lambda a: a['filename'])
        
        # Обновляем отображение с текущим фильтром
        self._apply_filter(self.search_input.text())
        
        # Устанавливаем директорию из первого архива если ещё не задана
        if archives and not self.archive_dir.exists():
            first_path = Path(archives[0]['path']).parent
            if first_path.exists():
                self.archive_dir = first_path
                set_last_archive_dir(first_path)

    def _scan_archives(self):
        """Сканировать каталог и заполнить таблицу архивами (.zip)."""
        try:
            self._all_archives = []  # Сохраняем все данные для фильтрации
            self.archive_table.setRowCount(0)
            if not self.archive_dir.exists():
                return

            for f in sorted(self.archive_dir.iterdir()):
                try:
                    # Только .zip архивы
                    if f.suffix.lower() == '.zip':
                        size_kb = f.stat().st_size / 1024
                        date_str = self._extract_date_from_filename(f.name)
                        turbine = self._extract_wtg_from_filename(f.name)
                        self._all_archives.append({
                            'turbine': turbine,
                            'date_str': date_str,
                            'size': f"{size_kb:.0f} КБ",
                            'path': str(f),
                            'filename': f.name
                        })
                except Exception:
                    continue

            self._apply_filter()
        except Exception as e:
            show_critical(self, "Ошибка", f"Ошибка сканирования:\n{str(e)}")

    def _filter_archives(self, text: str):
        """Фильтровать таблицу по введённому тексту."""
        self._apply_filter(text)

    def _clear_search(self):
        """Очистить поле поиска."""
        self.search_input.clear()
        self._apply_filter()

    def _apply_filter(self, filter_text: str = ""):
        """Применить фильтр к таблице архивов."""
        self.archive_table.setRowCount(0)
        
        filter_lower = filter_text.strip().lower()
        filtered = []
        
        for archive in self._all_archives:
            if not filter_lower:
                filtered.append(archive)
            else:
                # Поиск по турбине, дате и имени файла
                searchable = f"{archive['turbine']} {archive['date_str']} {archive['filename']}".lower()
                if filter_lower in searchable:
                    filtered.append(archive)
        
        if not filtered and self._all_archives:
            # Ничего не найдено
            self.archive_table.insertRow(0)
            no_result = QTableWidgetItem("Ничего не найдено")
            no_result.setFlags(Qt.ItemFlag.ItemIsEnabled)
            no_result.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            no_result.setForeground(QColor("#888888"))
            self.archive_table.setItem(0, 0, no_result)
            self.archive_table.setSpan(0, 0, 1, 3)
            return
        
        for row_idx, archive in enumerate(filtered):
            self.archive_table.insertRow(row_idx)
            item0 = QTableWidgetItem(archive['turbine'])
            item0.setData(Qt.ItemDataRole.UserRole, archive['path'])
            self.archive_table.setItem(row_idx, 0, item0)
            self.archive_table.setItem(row_idx, 1, QTableWidgetItem(archive['date_str']))
            self.archive_table.setItem(row_idx, 2, QTableWidgetItem(archive['size']))

    def _extract_date_from_filename(self, filename):
        match = re.search(r'(\d{8})', filename)
        if match:
            d = match.group(1)
            return f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
        try:
            mtime = (self.archive_dir / filename).stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
        except Exception:
            return "—"

    def _extract_turbine_from_filename(self, filename):
        """Извлечь идентификатор турбины из имени файла."""
        match = re.search(r'(WTG\d+|W\d+)', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return "Unknown"

    def _extract_wtg_from_filename(self, filename):
        """Извлечь наименование WTG турбины (WTG1...WTG57).

        Формат файла: 'W1436 WTG35 SMP_20250901_38408_SENSOR_01_FILTER_W.rd2'
        Возвращает: 'WTG35'
        """
        # Ищем WTG с номером (1-57)
        match = re.search(r'WTG(\d{1,2})', filename, re.IGNORECASE)
        if match:
            wtg_num = int(match.group(1))
            return f"WTG{wtg_num}"
        return "Unknown"

    def _on_archive_selected(self):
        """Обработка выбора архива в таблице."""
        # Блокируем если идёт загрузка
        if self._is_loading:
            return

        selected = self.archive_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.archive_table.item(row, 0)
        if item is None:
            return
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and Path(file_path).exists():
            self._parse_archive(file_path)

    def _load_rd2_file(self):
        """Открыть кастомный диалог выбора .rd2 файлов (мультивыбор)."""
        try:
            dialog = Rd2TreeDialog(self, str(self.archive_dir))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                files = dialog.get_selected_files()
                if files:
                    # Передаём первый файл или все файлы на обработку
                    self._parse_rd2_files(files)
        except Exception as e:
            show_critical(self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _load_archive(self):
        """Открыть кастомный диалог выбора .zip архива."""
        try:
            dialog = ArchiveTreeDialog(self, str(self.archive_dir))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                file_path = dialog.get_selected_file()
                if file_path:
                    self._parse_archive(file_path)
        except Exception as e:
            show_critical(self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _parse_rd2_files(self, file_paths):
        """Обработать несколько .rd2 файлов через MultiSensorRD2Parser.
        
        Args:
            file_paths: Список путей к .rd2 файлам (до 24 файлов).
        """
        if not file_paths:
            return

        # Для .rd2 файлов используем прямой парсинг без репозитория
        self.current_file = file_paths[0]  # Первый файл как основной
        self._is_loading = True
        
        # Блокируем таблицу и кнопки
        self.archive_table.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.load_rd2_btn.setEnabled(False)
        self.load_rd2_btn.setText("Загрузка...")
        self.analyze_btn.setEnabled(False)

        # Создаём парсер и добавляем файлы вручную
        parser = MultiSensorRD2Parser(file_paths[0])
        
        # Парсим все файлы
        for fp in file_paths:
            try:
                # Для каждого файла создаём отдельный парсер и合并яем данные
                single_parser = RD2Parser(fp)
                data = single_parser.parse()
                
                # Извлекаем sensor_id и filter_type из имени файла
                import re
                sensor_match = re.search(r'SENSOR_(\d{2})', fp)
                sensor_id = int(sensor_match.group(1)) if sensor_match else None
                
                filter_type = None
                filename_upper = Path(fp).name.upper()
                if '_FILTER_' in filename_upper or '_LOW_W' in filename_upper:
                    filter_type = 'LOW' if 'LOW' in filename_upper else 'FILTER'
                elif '_HIGH_' in filename_upper:
                    filter_type = 'HIGH'
                
                if sensor_id and filter_type:
                    if not parser.turbine_metadata:
                        parser.turbine_metadata = data['metadata']
                    
                    parser.sensor_data[sensor_id][filter_type] = {
                        'timestamps': data['timestamps'],
                        'values': data['values'],
                        'metadata': data['metadata']
                    }
                    parser._parsed = True
            except Exception as e:
                print(f"Ошибка парсинга {fp}: {e}")
                continue
        
        self._on_parse_finished(True, file_paths[0], parser)

    def _parse_archive(self, file_path):
        """Загрузить архив через репозиторий."""
        # Отменяем предыдущую загрузку если есть
        if hasattr(self, 'parse_thread') and self.parse_thread is not None:
            if self.parse_thread.isRunning():
                self.parse_thread.cancel()
                self.parse_thread.wait(1000)  # Ждём до 1 сек
        
        self.current_file = file_path
        self._is_loading = True
        
        # Блокируем таблицу и кнопки
        self.archive_table.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.load_rd2_btn.setEnabled(False)
        self.load_btn.setText("Загрузка...")
        self.analyze_btn.setEnabled(False)

        # Находим текущую строку и показываем спиннер
        current_row = self.archive_table.currentRow()
        if current_row >= 0:
            self._loading_row = current_row
            self._show_loading_spinner(current_row)

        # Передаём репозиторий и persistence_service в поток
        self.parse_thread = ParseThread(
            file_path, self.repository, self.persistence_service
        )
        self.parse_thread.finished.connect(self._on_parse_finished)
        self.parse_thread.error.connect(self._on_parse_error)
        self.parse_thread.load_result.connect(self._on_load_result)  # Новый сигнал
        self.parse_thread.start()

    # === Автопарсинг (v1.4) ===
    
    def _on_auto_scan_toggled(self, state):
        """Включить/выключить автопарсинг."""
        if self.auto_scan_service is not None:
            self.auto_scan_service.enabled = (state == Qt.CheckState.Checked)
            if self.auto_scan_service.enabled:
                self.auto_scan_service.start_timer(self)
            else:
                self.auto_scan_service.stop_timer()
    
    # === Конец автопарсинга ===

    def _on_load_result(self, result: Dict):
        """Обработчик результатов загрузки (дедупликация)."""
        # Сохраняем для использования в _on_parse_finished
        self._last_load_result = result
        
        # Логируем результаты
        added = result.get('added', 0)
        skipped = result.get('skipped', 0)
        errors = result.get('errors', [])
        
        if errors:
            for err in errors:
                logger.error("Ошибка загрузки: %s", err)
        
        if added > 0 or skipped > 0:
            logger.info("Результаты загрузки: добавлено=%d, пропущено=%d", added, skipped)

    def _on_parse_finished(self, success, file_path, parser):
        """Обработчик завершения загрузки."""
        self._hide_loading_spinner()
        self._is_loading = False
        
        # Разблокируем таблицу и кнопки
        self.archive_table.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.load_btn.setText("Загрузить архив .zip")
        self.load_rd2_btn.setEnabled(True)
        self.load_rd2_btn.setText("Загрузить файл .rd2")

        if not success:
            # Проверяем ошибки из результата загрузки
            errors = getattr(self, '_last_load_result', {}).get('errors', [])
            error_msg = errors[0] if errors else "Не удалось обработать архив."
            show_critical(self, "Ошибка", error_msg)
            return

        if parser is None:
            show_critical(self, "Ошибка", "Парсер не инициализирован.")
            return

        self.parser = parser
        self._update_sensor_statuses()
        self.analyze_btn.setEnabled(True)

        # Показываем результаты дедупликации
        result = getattr(self, '_last_load_result', {})
        added = result.get('added', 0)
        skipped = result.get('skipped', 0)
        
        if added > 0 or skipped > 0:
            # Показываем уведомление в статус-баре главного окна
            from .main_window import MainWindow
            main_win = self.window()
            if isinstance(main_win, MainWindow):
                if skipped > 0:
                    main_win.show_status_message(
                        f"Загружено: {added} новых, пропущено: {skipped} дубликатов",
                        "mdi.info"
                    )
                else:
                    main_win.show_status_message(
                        f"Загружено {added} новых записей",
                        "mdi.check-circle"
                    )

    def _on_parse_error(self, error_msg):
        """Обработчик ошибки загрузки."""
        self._hide_loading_spinner()
        self._is_loading = False
        
        # Разблокируем таблицу и кнопки
        self.archive_table.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.load_btn.setText("Загрузить архив .zip")
        self.load_rd2_btn.setEnabled(True)
        self.load_rd2_btn.setText("Загрузить файл .rd2")
        show_critical(self, "Ошибка", f"Ошибка при обработке:\n{error_msg}")

    def _show_loading_spinner(self, row):
        """Показать крутящийся спиннер справа от таблицы."""
        self._hide_loading_spinner()  # Скрыть предыдущий если есть
        
        if 0 <= row < self.archive_table.rowCount():
            self._loading_row = row
            # Родитель = HomeScreen (self), чтобы не обрезалось границами таблицы
            self._loading_spinner = LoadingSpinner(self)
            self._loading_spinner.start()
            
            # Позиционируем спиннер справа от таблицы
            item = self.archive_table.item(row, 2)  # Колонка 2 = "Размер"
            if item is None:
                return
            rect = self.archive_table.visualItemRect(item)
            
            # Конвертируем координаты из таблицы в глобальные, затем в локальные HomeScreen
            table_pos = self.archive_table.mapToGlobal(rect.topLeft())
            local_pos = self.mapFromGlobal(table_pos)
            
            # Справа от таблицы спиннер, центрирование по вертикали вниз
            x = local_pos.x() + rect.width() + 15
            y = local_pos.y() + (rect.height() - 10) // 2 + 27
            
            self._loading_spinner.move(x, y)
            self._loading_spinner.show()

    def _hide_loading_spinner(self):
        """Скрыть спиннер загрузки."""
        if self._loading_spinner is not None:
            self._loading_spinner.stop()
            self._loading_spinner.deleteLater()
            self._loading_spinner = None
        self._loading_row = -1

    def _update_sensor_statuses(self):
        """Обновить статусы всех 8 датчиков после парсинга файла.

        Логика определения статуса:
          • data is None               → 'empty' (датчик отсутствует в файле)
          • 3 сигнала (acc, vel, hf)   → 'ok'
          • 1–2 сигнала                → 'partial'
          • 0 сигналов                 → 'none' (датчик есть, но данных нет)
        """
        if not self.parser:
            return

        for sensor_id in range(1, 9):
            data = self.parser.get_sensor_data(sensor_id)
            if data is None:
                status = 'empty'
            else:
                has_acc = data['acceleration'] is not None
                has_vel = data['velocity'] is not None
                has_hf = data['high_freq'] is not None
                count = sum([has_acc, has_vel, has_hf])
                
                if count == 3:
                    status = 'ok'
                elif count > 0:
                    status = 'partial'
                else:
                    status = 'none'

            self.scheme.set_sensor_status(sensor_id, status)

            label = self.status_labels[sensor_id]
            if status == 'ok':
                label.setText("[ok]")
                label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold; background: transparent;")
            elif status == 'partial':
                label.setText("[частично]")
                label.setStyleSheet("color: #FFC107; font-size: 11px; font-weight: bold; background: transparent;")
            elif status == 'none':
                label.setText("[нет данных]")
                label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold; background: transparent;")
            else:
                label.setText("")
                label.setStyleSheet("color: #444444; font-size: 11px; font-weight: bold; background: transparent;")

    def _on_sensor_clicked(self, sensor_id):
        self.scheme.set_selected_sensor(sensor_id)
        for sid, label in self.status_labels.items():
            if sid == sensor_id:
                label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold; background-color: #333333;")
            else:
                self._update_sensor_statuses()
                break

    def _analyze(self):
        if self.parser:
            self.analyze_requested.emit(self.parser)

    def get_parser(self):
        return self.parser
