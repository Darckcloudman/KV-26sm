"""Графики временных рядов для вибрации."""

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
import numpy as np


class TimeSeriesChart(QWidget):
    """График временного ряда с адаптивным масштабированием."""

    def __init__(
        self,
        title: str,
        x_label: str = "Время",
        y_label: str = "Амплитуда",
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Настройка pyqtgraph для тёмной темы
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#121212')
        pg.setConfigOption('foreground', '#FFFFFF')

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle(self.title, color="#FFFFFF", size="11px")
        self.plot_widget.setLabel('bottom', self.x_label, color="#AAAAAA")
        self.plot_widget.setLabel('left', self.y_label, color="#AAAAAA")

        # Сетка
        self.plot_widget.getAxis('bottom').setGrid(128)
        self.plot_widget.getAxis('left').setGrid(128)

        # Стиль осей
        self.plot_widget.getAxis('bottom').setTextPen('#888888')
        self.plot_widget.getAxis('left').setTextPen('#888888')
        self.plot_widget.getAxis('bottom').setTickPen('#444444')
        self.plot_widget.getAxis('left').setTickPen('#444444')

        layout.addWidget(self.plot_widget)

        # Линия графика
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#FFFFFF', width=1.5)
        )

    def set_data(self, x_data: np.ndarray, y_data: np.ndarray) -> None:
        """
        Установить данные для графика.

        Args:
            x_data: Массив данных по оси X (время).
            y_data: Массив данных по оси Y (амплитуда).
        """
        self.curve.setData(x_data, y_data)

        # Авто-масштабирование Y
        if len(y_data) > 0:
            y_min = np.nanmin(y_data)
            y_max = np.nanmax(y_data)
            y_range = y_max - y_min

            # Добавляем отступ 10% сверху и снизу
            padding = y_range * 0.1 if y_range > 0 else 0.01
            self.plot_widget.setYRange(y_min - padding, y_max + padding)

    def clear(self) -> None:
        """Очистить график."""
        self.curve.clear()
        self.plot_widget.setYRange(0, 1)

    def clear_data(self) -> None:
        """Очистить данные графика (алиас для clear)."""
        self.clear()
