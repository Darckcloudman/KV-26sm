# -*- coding: utf-8 -*-
"""
Вкладка Home (home_screen.py)
==============================
Главный экран приложения SMP12C VibroDiag Analyzer.

Содержит:
  • Таблицу архивов (.zip / .rd2) с кастомным скроллбаром
  • Интерактивную схему турбины (shema.png) с 8 датчиками
  • Плавно мигающие индикаторы статуса (QVariantAnimation)
  • Список описаний датчиков с текстовым статусом

Статусы индикаторов (SensorIndicator):
  • empty   — датчик отсутствует в загруженном файле (прозрачный кружок,
              чёрная рамка 5 px, чёрный номер, без мигания)
  • ok      — все 3 типа сигналов загружены (зелёная рамка пульсирует
              плавно, прозрачный центр, чёрный номер)
  • partial — загружен 1–2 типа сигналов (жёлтая рамка пульсирует
              плавно, прозрачный центр, чёрный номер)
  • none    — датчик есть в файле, но данных нет (белая заливка,
              красная рамка 5 px, белый номер, без мигания)

Координаты SENSOR_POSITIONS зафиксированы вручную под shema.png.
Изменять только при замене изображения.
"""

import re
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QRect, QVariantAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPixmap, QPalette

from ..parsers.rd2_parser import MultiSensorRD2Parser


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


class ParseThread(QThread):
    finished = Signal(bool, str, object)
    error = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            parser = MultiSensorRD2Parser(self.file_path)
            success = parser.parse()
            self.finished.emit(success, self.file_path, parser)
        except Exception as e:
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
        self.setCursor(Qt.PointingHandCursor)

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(1200)
        self._animation.setEasingCurve(QEasingCurve.InOutSine)
        self._animation.valueChanged.connect(self._on_glow_changed)
        self._animation.finished.connect(self._on_animation_finished)

    def _on_glow_changed(self, value):
        self._glow = value
        self.update()

    def _on_animation_finished(self):
        if self._animation.direction() == QAbstractAnimation.Forward:
            self._animation.setDirection(QAbstractAnimation.Backward)
        else:
            self._animation.setDirection(QAbstractAnimation.Forward)
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
            if self._animation.state() != QAbstractAnimation.Running:
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
          empty   → чёрная рамка, прозрачный центр, чёрный номер
          ok      → зелёная пульсирующая рамка, прозрачный центр, чёрный номер
          partial → жёлтая пульсирующая рамка, прозрачный центр, чёрный номер
          none    → красная рамка, белый центр, белый номер
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = 11
        cx, cy = 13, 13

        if self.status == 'empty':
            border_color = QColor("#000000")
            fill_brush = Qt.NoBrush
            text_color = QColor("#000000")
        elif self.status == 'ok':
            bright = QColor("#4CAF50")
            dark = QColor("#1a4a1a")
            border_color = self._lerp_color(dark, bright, self._glow)
            fill_brush = Qt.NoBrush
            text_color = QColor("#000000")
        elif self.status == 'partial':
            bright = QColor("#FFC107")
            dark = QColor("#4a3a00")
            border_color = self._lerp_color(dark, bright, self._glow)
            fill_brush = Qt.NoBrush
            text_color = QColor("#000000")
        else:
            border_color = QColor("#F44336")
            fill_brush = QBrush(QColor("#FFFFFF"))
            text_color = QColor("#FFFFFF")

        painter.setBrush(fill_brush)
        painter.setPen(QPen(border_color, 5))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.setPen(QPen(text_color))
        font = QFont("Arial", 9, QFont.Bold)
        painter.setFont(font)
        text_rect = QRect(cx - r, cy - r, r * 2, r * 2)
        painter.drawText(text_rect, Qt.AlignCenter, str(self.sensor_id))

        if self.selected:
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cx - r - 2, cy - r - 2, (r + 2) * 2, (r + 2) * 2)

    def mousePressEvent(self, event):
        self.clicked.emit(self.sensor_id)


class SensorScheme(QFrame):
    """Схема турбины с shema.png и индикаторами."""
    sensor_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #000000; border: none;")

        self._pixmap = None
        self._scaled_pixmap = None
        self._indicators = []
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

        # Создаём индикаторы
        for i in range(8):
            indicator = SensorIndicator(i + 1, self)
            indicator.clicked.connect(self.sensor_clicked.emit)
            self._indicators.append(indicator)
            indicator.show()

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
        self._scaled_pixmap = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap_x = (w - self._scaled_pixmap.width()) // 2
        self._pixmap_y = (h - self._scaled_pixmap.height()) // 2
        self._scale = self._scaled_pixmap.width() / self._pixmap.width()

        for i, (rel_x, rel_y) in enumerate(SENSOR_POSITIONS):
            ind = self._indicators[i]
            x = self._pixmap_x + int(rel_x * self._pixmap.width() * self._scale) - 13
            y = self._pixmap_y + int(rel_y * self._pixmap.height() * self._scale) - 13
            ind.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self._scaled_pixmap and not self._scaled_pixmap.isNull():
            painter.drawPixmap(self._pixmap_x, self._pixmap_y, self._scaled_pixmap)


class HomeScreen(QWidget):
    """Вкладка Home."""
    analyze_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = None
        self.current_file = None
        self.archive_dir = Path(__file__).resolve().parent.parent.parent / "test_data"
        self._setup_ui()
        self._scan_archives()

    def _setup_ui(self):
        # Чёрный фон через палитру
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#000000"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 20, 60, 15)
        main_layout.setSpacing(14)

        # Заголовок
        title = QLabel("WTG Vibrodiag Analizer")
        title.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Кнопки + путь
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        left_top = QVBoxLayout()
        left_top.setSpacing(8)

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

        self.load_btn = QPushButton("Загрузить архив .zip или .rd2")
        self.load_btn.setStyleSheet(btn_style)
        self.load_btn.clicked.connect(self._load_archive)
        left_top.addWidget(self.load_btn)

        self.dir_btn = QPushButton("Выбрать место хранения архивов")
        self.dir_btn.setStyleSheet(btn_style)
        self.dir_btn.clicked.connect(self._select_directory)
        left_top.addWidget(self.dir_btn)

        self.path_label = QLabel(f"Путь к месту хранения архивов:\n{self.archive_dir}")
        self.path_label.setStyleSheet("color: #ffffff; font-size: 10px; background: transparent;")
        self.path_label.setWordWrap(True)
        left_top.addWidget(self.path_label)
        left_top.addStretch()

        top_layout.addLayout(left_top, 0)
        top_layout.addStretch(1)
        main_layout.addLayout(top_layout)

        # Таблица + Схема
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(4)

        # Таблица
        table_frame = QFrame()
        table_frame.setStyleSheet("QFrame { background-color: #ff0000; border: 1px solid #333333; border-radius: 4px; }")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(3)
        self.archive_table.setHorizontalHeaderLabels(["Турбина", "Дата записи", "Размер архива"])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archive_table.verticalHeader().setVisible(False)
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
        self.archive_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.archive_table.setSelectionMode(QTableWidget.SingleSelection)
        self.archive_table.itemSelectionChanged.connect(self._on_archive_selected)
        self.archive_table.setMinimumWidth(300)
        self.archive_table.setMaximumWidth(300)
        table_layout.addWidget(self.archive_table)

        middle_layout.addWidget(table_frame, 0)

        # Схема
        self.scheme = SensorScheme()
        self.scheme.sensor_clicked.connect(self._on_sensor_clicked)
        middle_layout.addWidget(self.scheme, 1)

        main_layout.addLayout(middle_layout, 2)

        # Список статусов
        status_frame = QFrame()
        status_frame.setStyleSheet("QFrame { background-color: #000000; border: 0px; border-radius: 0px; }")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        status_layout.setSpacing(4)

        self.status_labels = {}
        for i, desc in enumerate(SENSOR_DESCRIPTIONS):
            sensor_id = i + 1
            row = QHBoxLayout()
            row.setSpacing(8)

            num_label = QLabel(f"{sensor_id}.")
            num_label.setStyleSheet("color: #FFFFFF; font-size: 11px; background: transparent; min-width: 18px;")
            row.addWidget(num_label)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #BBBBBB; font-size: 11px; background: transparent;")
            row.addWidget(desc_label, 1)

            status_label = QLabel("[нет данных]")
            status_label.setStyleSheet("color: #F44336; font-size: 11px; font-weight: bold; background: transparent;")
            row.addWidget(status_label)

            self.status_labels[sensor_id] = status_label
            status_layout.addLayout(row)

        main_layout.addWidget(status_frame, 0)

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
        main_layout.addWidget(self.analyze_btn, alignment=Qt.AlignCenter)

        # Версия
        version_label = QLabel("v1.2 | A.Telezhenko, 2026")
        version_label.setStyleSheet("color: #444444; font-size: 9px; background: transparent;")
        version_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(version_label)

    def _select_directory(self):
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self, "Выберите каталог с архивами", str(self.archive_dir),
                QFileDialog.DontUseNativeDialog
            )
            if not dir_path:
                return
            self.archive_dir = Path(dir_path)
            self.path_label.setText(f"Путь к месту хранения архивов:\n{self.archive_dir}")
            self._scan_archives()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _scan_archives(self):
        try:
            self.archive_table.setRowCount(0)
            if not self.archive_dir.exists():
                return

            archives = []
            for f in sorted(self.archive_dir.iterdir()):
                try:
                    if f.suffix.lower() in ('.zip', '.rd2'):
                        size_kb = f.stat().st_size / 1024
                        date_str = self._extract_date_from_filename(f.name)
                        turbine = self._extract_turbine_from_filename(f.name)
                        archives.append((turbine, date_str, f"{size_kb:.0f} КБ", str(f)))
                except Exception:
                    continue

            for row_idx, (turbine, date_str, size, path) in enumerate(archives):
                self.archive_table.insertRow(row_idx)
                item0 = QTableWidgetItem(turbine)
                item0.setData(Qt.UserRole, path)
                self.archive_table.setItem(row_idx, 0, item0)
                self.archive_table.setItem(row_idx, 1, QTableWidgetItem(date_str))
                self.archive_table.setItem(row_idx, 2, QTableWidgetItem(size))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сканирования:\n{str(e)}")

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
        match = re.search(r'(WTG\d+|W\d+)', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return "Unknown"

    def _on_archive_selected(self):
        selected = self.archive_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.archive_table.item(row, 0)
        if item is None:
            return
        file_path = item.data(Qt.UserRole)
        if file_path and Path(file_path).exists():
            self._parse_archive(file_path)

    def _load_archive(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите архив", str(self.archive_dir),
                "Архивы и данные (*.zip *.rd2)",
                options=QFileDialog.DontUseNativeDialog
            )
            if file_path:
                self._parse_archive(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть диалог:\n{str(e)}")

    def _parse_archive(self, file_path):
        self.current_file = file_path
        self.load_btn.setEnabled(False)
        self.load_btn.setText("Загрузка...")
        self.analyze_btn.setEnabled(False)

        self.parse_thread = ParseThread(file_path)
        self.parse_thread.finished.connect(self._on_parse_finished)
        self.parse_thread.error.connect(self._on_parse_error)
        self.parse_thread.start()

    def _on_parse_finished(self, success, file_path, parser):
        self.load_btn.setEnabled(True)
        self.load_btn.setText("Загрузить архив .zip или .rd2")

        if not success:
            QMessageBox.critical(self, "Ошибка", "Не удалось обработать архив.")
            return

        self.parser = parser
        self._update_sensor_statuses()
        self.analyze_btn.setEnabled(True)

    def _on_parse_error(self, error_msg):
        self.load_btn.setEnabled(True)
        self.load_btn.setText("Загрузить архив .zip или .rd2")
        QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке:\n{error_msg}")

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
