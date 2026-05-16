"""Экран сырых данных — версия на QPainter"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
import numpy as np

SENSOR_DESCRIPTIONS = {
    1: "Главный вал радиальный",
    2: "Редуктор передняя нижняя часть радиальный",
    3: "Редуктор средняя часть радиальный",
    4: "Редуктор задняя часть радиальный",
    5: "Площадь выходного вала редуктора",
    6: "Подшипник генератора DE (осевой)",
    7: "Подшипник генератора DE (радиальный)",
    8: "Подшипник генератора NDE (радиальный)"
}


class RawDataCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.time_data = np.array([])
        self.signal_data = np.array([])
        self.sensor_id = 0
        self.sensor_name = ''

    def plot_raw_signal(self, time_data, signal_data, sensor_id, sensor_name):
        self.time_data = np.asarray(time_data)
        self.signal_data = np.asarray(signal_data)
        self.sensor_id = sensor_id
        self.sensor_name = sensor_name
        self.update()

    def show_no_data(self, sensor_id):
        self.time_data = np.array([])
        self.signal_data = np.array([])
        self.sensor_id = sensor_id
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#1a1a1a'))

        if len(self.time_data) == 0:
            painter.setPen(QColor('#666666'))
            painter.setFont(QFont('Consolas', 10))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Нет данных\nдля датчика %d' % self.sensor_id)
            return

        # Децимация
        t_data = self.time_data
        s_data = self.signal_data
        if len(t_data) > 5000:
            step = len(t_data) // 5000
            t_data = t_data[::step]
            s_data = s_data[::step]

        w, h = self.width(), self.height()
        m = 40
        max_t = float(t_data.max()) if len(t_data) else 1.0
        max_s = float(abs(s_data).max()) * 1.1 if len(s_data) else 1.0

        def tx(t): return m + (t / max_t) * (w - 2*m)
        def sy(v): return h//2 - (v / max_s) * (h//2 - m)

        # Оси
        painter.setPen(QPen(QColor('#333333'), 1))
        painter.drawLine(m, h//2, w-m, h//2)
        painter.drawLine(m, m, m, h-m)

        # Сигнал
        painter.setPen(QPen(QColor('#ff69b4'), 1))
        pts = [(tx(t), sy(v)) for t, v in zip(t_data, s_data)]
        for i in range(len(pts)-1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i+1][0]), int(pts[i+1][1]))

        # Заголовок
        painter.setPen(QColor('#ff69b4'))
        painter.setFont(QFont('Consolas', 9, QFont.Bold))
        painter.drawText(m, 15, 'Датчик %d -- %s' % (self.sensor_id, self.sensor_name))

        # Подписи
        painter.setPen(QColor('#888888'))
        painter.setFont(QFont('Consolas', 7))
        painter.drawText(w//2-20, h-5, 'Время, с')
        painter.drawText(5, h//2-10, 'м/с2')


class RawDataScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sensor_data = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("[=] СЫРЫЕ ДАННЫЕ [=]")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ff69b4; padding: 15px; border-bottom: 2px solid #333333;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #333333; background-color: #0a0a0a; border-radius: 5px; }")

        content = QWidget()
        grid = QGridLayout()
        grid.setSpacing(15)
        content.setLayout(grid)

        self.canvas_widgets = {}
        for sensor_id in range(1, 9):
            row = (sensor_id - 1) // 2
            col = (sensor_id - 1) % 2

            panel = QFrame()
            panel.setStyleSheet("QFrame { background-color: #1a1a1a; border: 2px solid #333333; border-radius: 8px; }")
            p_layout = QVBoxLayout()
            p_layout.setContentsMargins(10, 10, 10, 10)

            desc = SENSOR_DESCRIPTIONS.get(sensor_id, "Датчик %d" % sensor_id)
            header = QLabel("[%02d] %s" % (sensor_id, desc))
            header.setStyleSheet("font-size: 12px; font-weight: bold; color: #ff69b4; padding: 8px; background-color: #0a0a0a; border-radius: 4px;")
            header.setWordWrap(True)
            p_layout.addWidget(header)

            canvas = RawDataCanvas(self)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            p_layout.addWidget(canvas)

            panel.setLayout(p_layout)
            grid.addWidget(panel, row, col)
            self.canvas_widgets[sensor_id] = canvas

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        btn_layout = QHBoxLayout()
        self.btn_back = QPushButton("<- Назад к информации")
        self.btn_back.setFixedWidth(200)
        self.btn_back.clicked.connect(self._on_back)
        btn_layout.addWidget(self.btn_back)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def set_sensor_data(self, sensor_data):
        self._sensor_data = sensor_data
        for sensor_id in range(1, 9):
            canvas = self.canvas_widgets[sensor_id]
            if sensor_id in sensor_data:
                data = sensor_data[sensor_id]
                time_data = data.get('time', np.array([]))
                signal_data = data.get('signal', np.array([]))
                sensor_name = data.get('name', SENSOR_DESCRIPTIONS.get(sensor_id, "Датчик %d" % sensor_id))
                if len(time_data) > 0 and len(signal_data) > 0:
                    canvas.plot_raw_signal(time_data, signal_data, sensor_id, sensor_name)
                else:
                    canvas.show_no_data(sensor_id)
            else:
                canvas.show_no_data(sensor_id)

    def _on_back(self):
        if hasattr(self, '_on_back_callback'):
            self._on_back_callback()

    def set_back_callback(self, callback):
        self._on_back_callback = callback
