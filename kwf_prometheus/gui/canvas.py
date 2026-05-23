"""Графический компонент на QPainter — стабильная версия без matplotlib"""

import numpy as np
from typing import Optional, Callable

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush


class MplCanvas(QWidget):
    """Виджет для отрисовки графиков вибрации на QPainter"""

    def __init__(self, parent=None, width=10, height=5, dpi=100):
        super().__init__(parent)
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #000000;")

        self.frequencies = np.array([])
        self.amplitudes = np.array([])
        self.zone = 'A'
        self.rms = 0.0
        self._click_callback = None

    def set_click_callback(self, callback):
        self._click_callback = callback

    def plot_spectrum(self, frequencies, amplitudes, zone, rms_value):
        self.frequencies = np.asarray(frequencies)
        self.amplitudes = np.asarray(amplitudes)
        self.zone = zone
        self.rms = rms_value
        self.update()

    def clear(self):
        self.frequencies = np.array([])
        self.amplitudes = np.array([])
        self.update()

    def mousePressEvent(self, event):
        if self._click_callback and len(self.frequencies) > 0:
            x, y = self._screen_to_data(event.x(), event.y())
            if x is not None and y is not None:
                self._click_callback(x, y)

    def _screen_to_data(self, sx, sy):
        w, h = self.width(), self.height()
        margin = 60
        plot_w = w - 2 * margin
        plot_h = h - 2 * margin
        if plot_w <= 0 or plot_h <= 0:
            return None, None
        max_f = float(self.frequencies.max()) if len(self.frequencies) else 1.0
        max_a = float(self.amplitudes.max()) * 1.1 if len(self.amplitudes) else 10.0
        x = (sx - margin) / plot_w * max_f
        y = (h - margin - sy) / plot_h * max_a
        return x, y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#000000'))

        if len(self.frequencies) == 0:
            painter.setPen(QColor('#666666'))
            painter.setFont(QFont('Consolas', 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Загрузите данные для анализа')
            return

        w, h = self.width(), self.height()
        margin = 60
        plot_w = w - 2 * margin
        plot_h = h - 2 * margin
        max_f = float(self.frequencies.max()) if len(self.frequencies) else 1.0
        max_a = float(self.amplitudes.max()) * 1.1 if len(self.amplitudes) else 10.0

        def to_x(f): return margin + (f / max_f) * plot_w
        def to_y(a): return h - margin - (a / max_a) * plot_h

        # Оси
        painter.setPen(QPen(QColor('#333333'), 1))
        painter.drawLine(margin, h - margin, w - margin, h - margin)
        painter.drawLine(margin, margin, margin, h - margin)

        # Подписи
        painter.setPen(QColor('#a0a0a0'))
        painter.setFont(QFont('Consolas', 9))
        painter.drawText(5, h // 2, 'Ампл.')
        painter.drawText(w // 2 - 40, h - 5, 'Частота, Гц')

        # Границы зон
        zone_levels = [2.3, 4.5, 7.8]
        zone_colors = ['#555555', '#666666', '#777777']
        zone_labels = ['A/B', 'B/C', 'C/D']
        for level, color, label in zip(zone_levels, zone_colors, zone_labels):
            y = int(to_y(level))
            painter.setPen(QPen(QColor(color), 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin, y, w - margin, y)
            painter.setPen(QColor('#888888'))
            painter.setFont(QFont('Consolas', 8))
            painter.drawText(w - margin + 5, y + 3, label)

        # Спектр
        painter.setPen(QPen(QColor('#ff69b4'), 2))
        pts = [(to_x(f), to_y(a)) for f, a in zip(self.frequencies, self.amplitudes)]
        for i in range(len(pts) - 1):
            painter.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[i+1][0]), int(pts[i+1][1]))

        # Заголовок
        painter.setPen(QColor('#e0e0e0'))
        painter.setFont(QFont('Consolas', 10, QFont.Weight.Bold))
        painter.drawText(margin, 20, 'Спектр | Зона %s | СКЗ: %.3f мм/с' % (self.zone, self.rms))

        # Метки осей
        painter.setPen(QColor('#666666'))
        painter.setFont(QFont('Consolas', 8))
        for tick in np.linspace(0, max_f, 5):
            x = to_x(tick)
            painter.drawLine(int(x), h - margin, int(x), h - margin + 5)
            painter.drawText(int(x) - 15, h - margin + 18, '%.0f' % tick)
        for tick in np.linspace(0, max_a, 5):
            y = to_y(tick)
            painter.drawLine(margin - 5, int(y), margin, int(y))
            painter.drawText(margin - 45, int(y) + 3, '%.1f' % tick)
