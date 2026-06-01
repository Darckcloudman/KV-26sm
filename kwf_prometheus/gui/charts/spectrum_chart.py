"""Графики спектрального анализа с пороговыми линиями зон ISO 10816."""

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QTimer
import numpy as np
from typing import List


# Цвета зон ISO 10816
ZONE_COLORS = {
    'A': '#00C853',
    'B': '#FFD600',
    'C': '#FF6D00',
    'D': '#DD2C00',
}

# Пороги для ускорения (м/с²) — НЧ 0.1-10 Гц (SG132)
ACC_THRESHOLDS = {'A': 1.0, 'B': 2.5, 'C': 5.0}

# Пороги для скорости (мм/с) — ВЧ 10-1000 Гц (SG132)
# Базовый уровень (Норма): 1.5 - 3.5 мм/с
# Уставка предупреждения (Внимание): ~4.5-5.0 мм/с
# Уставка авария (Авария): 7.0-10.0 мм/с
VEL_THRESHOLDS = {'A': 3.5, 'B': 5.0, 'C': 7.5}


class PulsatingPeakMarker:
    """Анимированный пульсирующий маркер пика (Pulsating Peak Marker) с tooltip."""
    
    def __init__(self, plot_widget, x: float, y: float, number: int, 
                 base_size: float = 6.0, pulse_speed_ms: int = 1000):
        """
        Инициализация пульсирующего маркера пика.
        
        Args:
            plot_widget: PyqtGraph PlotWidget
            x: Координата X (частота)
            y: Координата Y (амплитуда)
            number: Номер пика (1, 2, 3...)
            base_size: Базовый размер точки в пикселях (диаметр)
            pulse_speed_ms: Скорость пульсации (полный цикл в мс)
        """
        self.plot_widget = plot_widget
        self.x = x
        self.y = y
        self.number = number
        self.base_size = base_size
        self.pulse_speed_ms = pulse_speed_ms
        self.visible = True
        
        # Текущий размер (будет анимироваться от base_size/2 до base_size*1.5)
        self.current_size = base_size
        self.pulse_phase = 0.0  # 0.0 - 1.0 (фаза синусоиды)
        
        # Создаём таймер для пульсации
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._update_pulse)
        # Обновляем 60 FPS для плавности
        self.pulse_timer.start(pulse_speed_ms // 60)
        
        # Красная точка с белым центром (стиль Home экрана)
        # Используем symbol='o' с красной заливкой и белым контуром
        self.scatter = pg.ScatterPlotItem(
            x=[x],
            y=[y],
            size=base_size,
            pen=pg.mkPen(color='#FFFFFF', width=1.5),  # Белый контур
            brush=pg.mkBrush(color='#DD2C00'),  # Красная заливка
            symbol='o',
            zValue=100
        )
        # Добавляем tooltip
        self.scatter.setToolTip(f'Пик #{number}\nЧастота: {x:.2f} Гц\nАмплитуда: {y:.6f}')
        self.plot_widget.addItem(self.scatter)
        
    def _update_pulse(self):
        """Обновить размер точки для эффекта пульсации."""
        # Синусоидальная пульсация: от 0.5x до 1.5x базового размера
        self.pulse_phase += 0.016  # ~60 FPS
        if self.pulse_phase > 6.28:  # 2*PI
            self.pulse_phase = 0.0
        
        # Амплитуда пульсации: 0.5 до 1.5 от базового размера
        scale = 1.0 + 0.5 * np.sin(self.pulse_phase)
        self.current_size = self.base_size * scale
        
        # Обновляем размер точки
        self.scatter.setSize(self.current_size)
    
    def update_position(self, x: float, y: float):
        """Обновить позицию маркера."""
        self.x = x
        self.y = y
        self.scatter.setData(x=[x], y=[y])
        self.scatter.setToolTip(f'Пик #{self.number}\nЧастота: {x:.2f} Гц\nАмплитуда: {y:.6f}')
    
    def set_number(self, number: int):
        """Обновить номер пика."""
        self.number = number
        self.scatter.setToolTip(f'Пик #{number}\nЧастота: {self.x:.2f} Гц\nАмплитуда: {self.y:.6f}')
    
    def hide(self):
        """Скрыть маркер."""
        self.visible = False
        self.scatter.hide()
        self.pulse_timer.stop()
    
    def show(self):
        """Показать маркер."""
        self.visible = True
        self.scatter.show()
        self.pulse_timer.start()
    
    def cleanup(self):
        """Удалить маркер из графика и остановить таймер."""
        self.pulse_timer.stop()
        self.plot_widget.removeItem(self.scatter)


class SpectrumChart(QWidget):
    """График спектра с пороговыми линиями и подсветкой зон ISO 10816."""

    def __init__(
        self,
        title: str,
        x_label: str = "Частота (Гц)",
        y_label: str = "Амплитуда",
        freq_range: tuple = (0, 1000),
        thresholds: dict | None = None,
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
        self._peak_markers: List[PulsatingPeakMarker] = []
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
                    pen=pg.mkPen(color=color, width=1, style=Qt.PenStyle.DashLine)
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
        peak_range: tuple | None = None,
        peak_frequencies: list | None = None,
        peak_numbers: list | None = None
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
        else:
            self.plot_widget.setYRange(0, 1)

    def _add_peak_markers(
        self,
        freq_data: np.ndarray,
        amplitude_data: np.ndarray,
        peak_frequencies: list,
        peak_numbers: list | None = None
    ) -> None:
        """
        Добавить пульсирующие маркеры пиков на график.

        Args:
            freq_data: Массив частот (уже отфильтрованный по диапазону графика).
            amplitude_data: Массив амплитуд (уже отфильтрованный).
            peak_frequencies: Список частот пиков для отображения.
            peak_numbers: Список номеров пиков из таблицы.
        """
        # Удаляем старые маркеры
        self._clear_peak_markers()

        if not peak_frequencies:
            print(f"[DEBUG] SpectrumChart '{self.title}': Нет пиков для отображения")
            return

        # Если номера пиков не переданы, используем порядковые номера
        if peak_numbers is None or len(peak_numbers) == 0:
            peak_numbers = list(range(1, len(peak_frequencies) + 1))

        # Проверяем, что есть данные
        if len(freq_data) == 0:
            print(f"[DEBUG] SpectrumChart '{self.title}': Нет данных частоты")
            return

        # Получаем максимальную частоту в данных (важно для ВЧ спектра!)
        max_data_freq = np.max(freq_data)
        min_data_freq = np.min(freq_data)

        print(f"[DEBUG] SpectrumChart '{self.title}': data_range=({min_data_freq:.2f}-{max_data_freq:.2f}), peaks_to_show={len(peak_frequencies)}, freqs={peak_frequencies}")

        # Ищем и отображаем пики
        for i, peak_freq in enumerate(peak_frequencies[:10]):
            # ПРОВЕРКА 1: Пик не должен быть дальше максимальной частоты данных
            if peak_freq > max_data_freq * 1.1:  # 10% запас
                print(f"[DEBUG] Пропуск пика {peak_numbers[i] if i < len(peak_numbers) else i+1} на {peak_freq:.2f} Гц (max_data={max_data_freq:.2f})")
                continue  # Пик вне диапазона данных, пропускаем

            # Ищем ближайшее значение частоты в данных графика
            closest_idx = np.argmin(np.abs(freq_data - peak_freq))
            closest_freq = freq_data[closest_idx]
            peak_amp = amplitude_data[closest_idx]

            # Получаем номер пика из таблицы
            peak_number = peak_numbers[i] if i < len(peak_numbers) else (i + 1)

            print(f"[DEBUG] Добавлен пульсирующий пик #{peak_number} на {peak_freq:.2f} Гц, amp={peak_amp:.6f}")

            # Создаём пульсирующий маркер (Pulsating Peak Marker)
            marker = PulsatingPeakMarker(
                self.plot_widget,
                x=peak_freq,
                y=peak_amp,
                number=peak_number,
                base_size=6.0,  # Базовый размер 6px
                pulse_speed_ms=1000  # Скорость пульсации 1 секунда
            )
            self._peak_markers.append(marker)

    def _clear_peak_markers(self) -> None:
        """Удалить все маркеры пиков."""
        for marker in self._peak_markers:
            marker.cleanup()
        self._peak_markers.clear()

    def clear(self) -> None:
        """Очистить график."""
        self.curve.clear()
        if hasattr(self, 'highlight_item') and self.highlight_item:
            self.plot_widget.removeItem(self.highlight_item)
            self.highlight_item = None
        for item in self._zone_items:
            self.plot_widget.removeItem(item)
        self._zone_items.clear()
        for line in self._threshold_lines:
            self.plot_widget.removeItem(line)
        self._threshold_lines.clear()
        # Очистка маркеров пиков
        self._clear_peak_markers()
        self.plot_widget.setYRange(0, 1)

    def clear_data(self) -> None:
        """Очистить данные графика (алиас для clear)."""
        self.clear()
