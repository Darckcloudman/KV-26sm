"""Экран сырых данных v1.4 — с масштабированием и курсором"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy, QSlider,
    QToolTip
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QMouseEvent
import numpy as np

from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY, COLOR_BG_DARK,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_BORDER,
    FONT_FAMILY, FONT_FAMILY_MONO,
    BUTTON_STYLE, BUTTON_SMALL_STYLE, PANEL_STYLE
)

SENSOR_DESCRIPTIONS = {
    1: "Главный вал, радиальное направление",
    2: "Передняя нижняя часть редуктора",
    3: "Средняя нижняя часть редуктора",
    4: "Выход трансмиссии, радиальное направление",
    5: "Выход трансмиссии, осевое направление",
    6: "Подшипник генератора со стороны ротора, осевое",
    7: "Подшипник генератора со стороны ротора, радиальное",
    8: "Подшипник генератора, осевое направление",
}


class RawDataCanvas(QWidget):
    """Холст для отрисовки сырых данных с масштабированием и курсором."""
    
    zoom_changed = Signal(float)  # Сигнал изменения масштаба
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.setCursor(Qt.CrossCursor)
        
        # Данные
        self.time_data = np.array([])
        self.signal_data = np.array([])
        self.sensor_id = 0
        self.sensor_name = ''

        # Масштабирование
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.scroll_offset = 0  # Прокрутка по времени
        
        # Курсор
        self.cursor_x = -1
        self.cursor_y = -1
        self.show_cursor = False
        
        # Настройки отрисовки
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.NoContextMenu)

    def plot_raw_signal(self, time_data, signal_data, sensor_id, sensor_name):
        """Установить данные для отрисовки."""
        self.time_data = np.asarray(time_data, dtype=np.float64)
        self.signal_data = np.asarray(signal_data, dtype=np.float64)
        self.sensor_id = sensor_id
        self.sensor_name = sensor_name
        self.zoom_level = 1.0
        self.scroll_offset = 0
        self.update()

    def show_no_data(self, sensor_id):
        """Показать заглушку при отсутствии данных."""
        self.time_data = np.array([])
        self.signal_data = np.array([])
        self.sensor_id = sensor_id
        self.update()

    def set_zoom(self, zoom: float):
        """Установить уровень масштабирования."""
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, zoom))
        self.update()
        self.zoom_changed.emit(self.zoom_level)

    def wheelEvent(self, event):
        """Обработка колёсика мыши для масштабирования."""
        if len(self.time_data) == 0:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1
        
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level))
        self.update()
        self.zoom_changed.emit(self.zoom_level)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши для курсора."""
        if len(self.time_data) == 0:
            return
        
        self.cursor_x = event.pos().x()
        self.cursor_y = event.pos().y()
        self.show_cursor = True
        
        # Вычисляем координаты данных под курсором
        w, h = self.width(), self.height()
        m = 50
        plot_w = w - 2 * m
        plot_h = h - 2 * m
        
        if len(self.time_data) > 0:
            # Децимация для отображения
            t_data = self.time_data
            s_data = self.signal_data
            if len(t_data) > 5000:
                step = len(t_data) // 5000
                t_data = t_data[::step]
                s_data = s_data[::step]
            
            max_t = float(t_data.max()) if len(t_data) else 1.0
            max_s = float(abs(s_data).max()) * 1.1 if len(s_data) else 1.0
            
            # Обратное преобразование координат
            if m <= self.cursor_x <= w - m and m <= self.cursor_y <= h - m:
                t_val = ((self.cursor_x - m) / plot_w) * (max_t * self.zoom_level)
                s_val = max_s - ((self.cursor_y - m) / plot_h) * (2 * max_s)
                
                # Показываем tooltip с координатами
                QToolTip.showText(
                    self.mapToGlobal(event.pos()),
                    f"Время: {t_val:.3f} с\nАмплитуда: {s_val:.3f} м/с²",
                    self
                )
        
        self.update()

    def leaveEvent(self, event):
        """Скрыть курсор при уходе мыши."""
        self.show_cursor = False
        self.update()

    def paintEvent(self, event):
        """Отрисовка графика."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))

            if len(self.time_data) == 0 or len(self.signal_data) == 0:
                painter.setPen(QColor(COLOR_TEXT_PRIMARY))
                painter.setFont(QFont(FONT_FAMILY_MONO, 12, QFont.Weight.Bold))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Нет данных\nдля датчика {self.sensor_id}')
                return

            # Децимация для производительности
            t_data = self.time_data
            s_data = self.signal_data
            if len(t_data) > 5000:
                step = len(t_data) // 5000
                t_data = t_data[::step]
                s_data = s_data[::step]

            w, h = self.width(), self.height()
            if w < 100 or h < 100:
                return  # Слишком маленький размер
            
            m = 50  # Отступы
            plot_w = w - 2 * m
            plot_h = h - 2 * m
            
            # Масштабирование
            max_t = float(t_data.max()) if len(t_data) > 0 else 1.0
            max_s = float(abs(s_data).max()) * 1.1 if len(s_data) > 0 else 1.0
            
            if max_t <= 0:
                max_t = 1.0
            if max_s <= 0:
                max_s = 1.0
            
            scaled_max_t = max_t * self.zoom_level

            def tx(t):
                return m + (t / scaled_max_t) * plot_w if scaled_max_t > 0 else m
            
            def sy(v):
                if max_s > 0:
                    return h - m - ((v + max_s) / (2 * max_s)) * plot_h
                return h // 2

            # Сетка
            painter.setPen(QPen(QColor(COLOR_BORDER), 1))
            for i in range(5):
                y = m + i * (plot_h // 4)
                painter.drawLine(m, y, w - m, y)
            for i in range(6):
                x = m + i * (plot_w // 5)
                painter.drawLine(x, m, x, h - m)

            # Оси
            painter.setPen(QPen(QColor(COLOR_ACCENT), 2))
            painter.drawLine(m, h - m, w - m, h - m)  # Ось X
            painter.drawLine(m, m, m, h - m)  # Ось Y

            # Сигнал
            painter.setPen(QPen(QColor(COLOR_ACCENT), 1))
            pts = [(tx(t), sy(v)) for t, v in zip(t_data, s_data)]
            for i in range(len(pts) - 1):
                if m <= pts[i][0] <= w - m and m <= pts[i][1] <= h - m:
                    painter.drawLine(
                        int(pts[i][0]), int(pts[i][1]),
                        int(pts[i + 1][0]), int(pts[i + 1][1])
                    )

            # Курсор
            if self.show_cursor and m <= self.cursor_x <= w - m and m <= self.cursor_y <= h - m:
                painter.setPen(QPen(QColor("#FF6B6B"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(self.cursor_x, m, self.cursor_x, h - m)
                painter.drawLine(m, self.cursor_y, w - m, self.cursor_y)

            # Заголовок
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Weight.Bold))
            painter.drawText(m, 20, f'Датчик {self.sensor_id} — {self.sensor_name}')

            # Подписи осей
            painter.setPen(QColor(COLOR_TEXT_TERTIARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 8))
            painter.drawText(w // 2 - 30, h - 10, 'Время, с')
            painter.drawText(5, h // 2 - 5, 'м/с²')
            
            # Масштаб
            painter.drawText(w - 100, 20, f'Zoom: {self.zoom_level:.1f}x')
        except Exception as e:
            # Если ошибка отрисовки — показываем сообщение
            painter = QPainter(self)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Ошибка отрисовки:\n{str(e)}')


class SensorSelector(QFrame):
    """Панель выбора датчика с 8 кнопками (разделены на группы)."""
    
    sensor_selected = Signal(int)  # Сигнал выбора датчика
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_TERTIARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        self.selected_sensor = 1
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)
        
        # Группа 1: Редуктор (датчики 1-5)
        gearbox_layout = QHBoxLayout()
        gearbox_layout.setSpacing(4)
        gearbox_label = QLabel('Редуктор:')
        gearbox_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 9px; font-weight: bold;")
        gearbox_layout.addWidget(gearbox_label)
        
        self.buttons = {}
        for sensor_id in range(1, 6):
            btn = QPushButton(str(sensor_id))
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BG_SECONDARY};
                    color: {COLOR_TEXT_SECONDARY};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_TERTIARY};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {COLOR_ACCENT};
                    color: {COLOR_BG_PRIMARY};
                    border: 1px solid {COLOR_ACCENT};
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, sid=sensor_id: self._on_sensor_clicked(sid))
            gearbox_layout.addWidget(btn)
            self.buttons[sensor_id] = btn
        
        main_layout.addLayout(gearbox_layout)
        
        # Группа 2: Генератор (датчики 6-8)
        generator_layout = QHBoxLayout()
        generator_layout.setSpacing(4)
        generator_label = QLabel('Генератор:')
        generator_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 9px; font-weight: bold;")
        generator_layout.addWidget(generator_label)
        
        for sensor_id in range(6, 9):
            btn = QPushButton(str(sensor_id))
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BG_SECONDARY};
                    color: {COLOR_TEXT_SECONDARY};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_TERTIARY};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QPushButton:checked {{
                    background-color: {COLOR_ACCENT};
                    color: {COLOR_BG_PRIMARY};
                    border: 1px solid {COLOR_ACCENT};
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, sid=sensor_id: self._on_sensor_clicked(sid))
            generator_layout.addWidget(btn)
            self.buttons[sensor_id] = btn
        
        main_layout.addLayout(generator_layout)
        
        # Выделяем первый датчик
        self.buttons[1].setChecked(True)
    
    def _on_sensor_clicked(self, sensor_id: int):
        self.selected_sensor = sensor_id
        for sid, btn in self.buttons.items():
            btn.setChecked(sid == sensor_id)
        self.sensor_selected.emit(sensor_id)
    
    def set_selected(self, sensor_id: int):
        if sensor_id in self.buttons:
            self.buttons[sensor_id].setChecked(True)


class RawDataScreen(QWidget):
    """Экран сырых данных с переключением датчиков и масштабированием."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sensor_data = {}
        self._current_sensor = 1
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)

        # Заголовок + селектор датчиков
        header_layout = QHBoxLayout()
        
        title = QLabel("СЫРЫЕ ДАННЫЕ")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Селектор датчиков
        sensor_label = QLabel("Датчик:")
        sensor_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        header_layout.addWidget(sensor_label)
        
        self.sensor_selector = SensorSelector(self)
        self.sensor_selector.sensor_selected.connect(self._on_sensor_selected)
        header_layout.addWidget(self.sensor_selector)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Подпись датчика
        self.sensor_desc_label = QLabel(SENSOR_DESCRIPTIONS.get(1, ""))
        self.sensor_desc_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")
        self.sensor_desc_label.setWordWrap(True)
        layout.addWidget(self.sensor_desc_label)

        # Холст с графиком
        self.canvas = RawDataCanvas(self)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas, stretch=1)

        # Слайдер масштабирования
        zoom_layout = QHBoxLayout()
        zoom_label = QLabel("Масштаб:")
        zoom_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        zoom_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(200)
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLOR_BG_TERTIARY};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_ACCENT};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLOR_ACCENT_HOVER};
            }}
        """)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px; min-width: 40px;")
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)

        # Кнопки навигации
        btn_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Назад")
        self.btn_back.setStyleSheet(BUTTON_STYLE)
        self.btn_back.setFixedWidth(150)
        self.btn_back.clicked.connect(self._on_back)
        btn_layout.addWidget(self.btn_back)
        
        self.btn_analyze = QPushButton("Перейти к анализу →")
        self.btn_analyze.setStyleSheet(BUTTON_STYLE)
        self.btn_analyze.setFixedWidth(180)
        self.btn_analyze.clicked.connect(self._on_analyze)
        btn_layout.addWidget(self.btn_analyze)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_sensor_selected(self, sensor_id: int):
        """Обработка выбора датчика."""
        self._current_sensor = sensor_id
        self.sensor_desc_label.setText(SENSOR_DESCRIPTIONS.get(sensor_id, ""))
        
        # Показываем данные выбранного датчика
        if sensor_id in self._sensor_data:
            data = self._sensor_data[sensor_id]
            time_data = data.get('time', np.array([]))
            signal_data = data.get('signal', np.array([]))
            sensor_name = data.get('name', SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}"))
            if len(time_data) > 0 and len(signal_data) > 0:
                self.canvas.plot_raw_signal(time_data, signal_data, sensor_id, sensor_name)
            else:
                self.canvas.show_no_data(sensor_id)
        else:
            self.canvas.show_no_data(sensor_id)

    def _on_zoom_changed(self, value: int):
        """Обработка изменения слайдера масштаба."""
        zoom = value / 10.0
        self.canvas.set_zoom(zoom)
        self.zoom_label.setText(f"{zoom:.1f}x")

    def set_sensor_data(self, sensor_data):
        """Установить данные датчиков."""
        self._sensor_data = sensor_data
        
        # Проверяем, есть ли данные
        available_sensors = [sid for sid in range(1, 9) if sid in sensor_data and len(sensor_data[sid].get('time', [])) > 0]
        
        if available_sensors:
            # Показываем первый доступный датчик
            self._on_sensor_selected(available_sensors[0])
        else:
            self.canvas.show_no_data(1)

    def _on_back(self):
        if hasattr(self, '_on_back_callback'):
            self._on_back_callback()

    def _on_analyze(self):
        if hasattr(self, '_on_analyze_callback'):
            self._on_analyze_callback()

    def set_back_callback(self, callback):
        self._on_back_callback = callback

    def set_analyze_callback(self, callback):
        self._on_analyze_callback = callback
