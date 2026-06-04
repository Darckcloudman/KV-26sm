"""Графики спектрального анализа с пороговыми линиями зон ISO 10816."""

import pyqtgraph as pg
from pyqtgraph import InfiniteLine, TextItem, ScatterPlotItem
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
import numpy as np
from typing import List, Optional


# Цвета зон ISO 10816
ZONE_COLORS = {
    'A': '#00C853',
    'B': '#FFD600',
    'C': '#FF6D00',
    'D': '#DD2C00',
}

# Пороги для ускорения (м/с²) — НЧ 0.1-10 Гц
ACC_THRESHOLDS = {'A': 1.0, 'B': 2.5, 'C': 5.0}
# Пороги для скорости (мм/с) — ВЧ 10-1000 Гц
VEL_THRESHOLDS = {'A': 2.3, 'B': 4.5, 'C': 11.2}


class SpectrumChart(QWidget):
    """График спектра с пороговыми линиями и подсветкой зон ISO 10816."""

    def __init__(
        self,
        title: str,
        x_label: str = "Частота (Гц)",
        y_label: str = "Амплитуда",
        freq_range: tuple = (0, 1000),
        thresholds: dict = None,
        highlight_peaks: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.freq_range = freq_range
        self.thresholds = thresholds
        self.highlight_peaks = highlight_peaks
        self._zone_items = []
        self._threshold_lines = []
        self._peak_markers: List[ScatterPlotItem] = []
        self._peak_text_items: List[TextItem] = []
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#000000')
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

        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#FFFFFF', width=1.5)
        )

        # Область подсветки пиков (опционально)
        self.highlight_item = None

    def _draw_zone_backgrounds(self, y_max: float) -> None:
        """Нарисовать цветные фоны для зон A/B/C/D (горизонтальные полосы)."""
        # Удаляем старые зоны
        for item in self._zone_items:
            self.plot_widget.removeItem(item)
        self._zone_items.clear()

        if not self.thresholds:
            return

        try:
            # Зона A: 0 до A (зелёная, полупрозрачная)
            zone_a = pg.LinearRegionItem(
                values=[0, self.thresholds['A']],
                orientation='horizontal',
                brush=QColor(0, 200, 83, 25),
                movable=False
            )
            self.plot_widget.addItem(zone_a)
            self._zone_items.append(zone_a)

            # Зона B: A до B (жёлтая)
            zone_b = pg.LinearRegionItem(
                values=[self.thresholds['A'], self.thresholds['B']],
                orientation='horizontal',
                brush=QColor(255, 214, 0, 20),
                movable=False
            )
            self.plot_widget.addItem(zone_b)
            self._zone_items.append(zone_b)

            # Зона C: B до C (оранжевая)
            zone_c = pg.LinearRegionItem(
                values=[self.thresholds['B'], self.thresholds['C']],
                orientation='horizontal',
                brush=QColor(255, 109, 0, 15),
                movable=False
            )
            self.plot_widget.addItem(zone_c)
            self._zone_items.append(zone_c)

            # Зона D: выше C (красная)
            zone_d = pg.LinearRegionItem(
                values=[self.thresholds['C'], y_max * 1.2],
                orientation='horizontal',
                brush=QColor(221, 44, 0, 10),
                movable=False
            )
            self.plot_widget.addItem(zone_d)
            self._zone_items.append(zone_d)
        except Exception:
            # Если orientation='horizontal' не поддерживается, пропускаем фоны
            pass

    def _draw_threshold_lines(self) -> None:
        """Нарисовать пунктирные линии порогов."""
        # Удаляем старые линии
        for line in self._threshold_lines:
            self.plot_widget.removeItem(line)
        self._threshold_lines.clear()

        if not self.thresholds:
            return

        for zone, value in self.thresholds.items():
            try:
                color = ZONE_COLORS.get(zone, '#FFFFFF')
                line = pg.InfiniteLine(
                    pos=value,
                    angle=0,
                    pen=pg.mkPen(color=color, width=1, style=Qt.DashLine)
                )
                self.plot_widget.addItem(line)
                self._threshold_lines.append(line)
            except Exception:
                # Игнорируем ошибки добавления линий
                pass

    def set_data(
        self,
        freq_data: np.ndarray,
        amplitude_data: np.ndarray,
        peak_range: tuple = None,
        peak_frequencies: Optional[List[float]] = None,
        peak_numbers: Optional[List[int]] = None
    ) -> None:
        """
        Установить данные для спектра.

        Args:
            freq_data: Массив частот (Гц).
            amplitude_data: Массив амплитуд.
            peak_range: Диапазон частот для подсветки пиков (min_freq, max_freq).
            peak_frequencies: Список частот пиков для отображения с нумерацией.
            peak_numbers: Список номеров пиков из таблицы (для соответствия нумерации).
        """
        # Фильтруем данные по диапазону частот
        mask = (freq_data >= self.freq_range[0]) & (freq_data <= self.freq_range[1])
        freq_filtered = freq_data[mask]
        amplitude_filtered = amplitude_data[mask]

        self.curve.setData(freq_filtered, amplitude_filtered)

        # Авто-масштабирование Y
        if len(amplitude_filtered) > 0:
            y_max = np.nanmax(amplitude_filtered)
            y_range = y_max if y_max > 0 else 0.01
            self.plot_widget.setYRange(0, y_range * 1.1)

            # Рисуем зоны и пороги
            self._draw_zone_backgrounds(y_range * 1.1)
            self._draw_threshold_lines()

            # Отображаем пики с нумерацией
            if peak_frequencies and len(peak_frequencies) > 0:
                self._add_peak_markers(freq_filtered, amplitude_filtered, peak_frequencies, peak_numbers)

        # Подсветка пиков (старый метод)
        if self.highlight_peaks and peak_range:
            self._add_peak_highlight(peak_range)

    def _add_peak_highlight(self, peak_range: tuple) -> None:
        """Добавить полупрозрачную подсветку области пиков."""
        if self.highlight_item:
            self.plot_widget.removeItem(self.highlight_item)

        min_freq, max_freq = peak_range
        view_range = self.plot_widget.viewRange()
        y_max = view_range[1][1] if view_range else 1.0

        self.highlight_item = pg.LinearRegionItem(
            values=[min_freq, max_freq],
            brush=QColor(0, 200, 83, 30),
            movable=False
        )
        self.plot_widget.addItem(self.highlight_item)

    def _add_peak_markers(
        self,
        freq_data: np.ndarray,
        amplitude_data: np.ndarray,
        peak_frequencies: List[float],
        peak_numbers: Optional[List[int]] = None
    ) -> None:
        """
        Добавить жёлтые маркеры пиков на график.

        Args:
            freq_data: Массив частот (уже отфильтрованный по диапазону графика).
            amplitude_data: Массив амплитуд (уже отфильтрованный).
            peak_frequencies: Список частот пиков для отображения.
            peak_numbers: Список номеров пиков из таблицы.
        """
        # Удаляем старые маркеры
        self._clear_peak_markers()

        if not peak_frequencies:
            return

        # Если номера пиков не переданы, используем порядковые номера
        if peak_numbers is None or len(peak_numbers) == 0:
            peak_numbers = list(range(1, len(peak_frequencies) + 1))

        # Проверяем, что есть данные
        if len(freq_data) == 0:
            return

        # Получаем максимальную частоту в данных
        max_data_freq = np.max(freq_data)

        # Ищем и отображаем пики
        for i, peak_freq in enumerate(peak_frequencies[:10]):
            # ПРОВЕРКА: Пик не должен быть дальше максимальной частоты данных
            if peak_freq > max_data_freq * 1.1:  # 10% запас
                continue  # Пик вне диапазона данных, пропускаем

            # Ищем ближайшее значение частоты в данных графика
            closest_idx = np.argmin(np.abs(freq_data - peak_freq))
            closest_freq = freq_data[closest_idx]
            peak_amp = amplitude_data[closest_idx]

            # Получаем номер пика из таблицы
            peak_number = peak_numbers[i] if i < len(peak_numbers) else (i + 1)

            # Создаём ScatterPlotItem для позиции на графике
            marker_scatter = ScatterPlotItem(
                x=[peak_freq],
                y=[peak_amp],
                size=10,  # Размер точки
                pen=pg.mkPen(color='#FFD600', width=2),  # Жёлтая обводка
                brush=pg.mkBrush(color='#FFD600'),  # Жёлтая заливка
                symbol='o',
                zValue=100
            )
            
            # Добавляем tooltip
            tooltip_text = f'Пик #{peak_number}\nЧастота: {peak_freq:.2f} Гц\nАмплитуда: {peak_amp:.6f}'
            marker_scatter.setToolTip(tooltip_text)
            
            # Добавляем на график
            self.plot_widget.addItem(marker_scatter)
            self._peak_markers.append(marker_scatter)
            
            # Добавляем текстовую метку с номером пика
            text = TextItem(
                text=f'#{peak_number}',
                color='#FFD600',
                fill='#000000',
                anchor=(0.5, 0),
                size=10
            )
            text.setPos(peak_freq, peak_amp)
            self.plot_widget.addItem(text)
            self._peak_text_items.append(text)

    def _clear_peak_markers(self) -> None:
        """Очистить маркеры пиков."""
        for item in self._peak_markers:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._peak_markers.clear()

        for item in self._peak_text_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._peak_text_items.clear()

    def clear(self) -> None:
        """Очистить график."""
        self.curve.clear()
        if self.highlight_item:
            self.plot_widget.removeItem(self.highlight_item)
            self.highlight_item = None
        for item in self._zone_items:
            self.plot_widget.removeItem(item)
        self._zone_items.clear()
        for line in self._threshold_lines:
            self.plot_widget.removeItem(line)
        self._threshold_lines.clear()
        self._clear_peak_markers()  # Очищаем маркеры пиков
        self.plot_widget.setYRange(0, 1)

    def clear_data(self) -> None:
        """Очистить данные графика (алиас для clear)."""
        self.clear()
