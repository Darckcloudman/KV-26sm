"""Компонент графика matplotlib для PyQt5"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from typing import Optional


class MplCanvas(FigureCanvasQTAgg):
    """График matplotlib для интеграции в PyQt5"""
    
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        """
        Инициализация канваса
        
        Args:
            parent: родительский виджет
            width: ширина графика в дюймах
            height: высота графика в дюймах
            dpi: разрешение
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        
        self.setParent(parent)
        
        # Настройки графика
        self(fig).set_size_policy(1, 1)  # QSizePolicy.Expanding
        self(fig).updateGeometry()
        
        # Обработчик клика
        self._click_callback = None
        self.mpl_connect('button_press_event', self._on_click)
    
    def _on_click(self, event):
        """Обработка клика по графику"""
        if event.inaxes == self.ax and self._click_callback:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                self._click_callback(x, y)
    
    def set_click_callback(self, callback):
        """
        Установка Callback для клика
        
        Args:
            callback: функция callback(x, y)
        """
        self._click_callback = callback
    
    def plot_spectrum(self, frequencies: np.ndarray, amplitudes: np.ndarray, 
                     zone: str, rms_value: float):
        """
        Построение спектра вибрации
        
        Args:
            frequencies: массив частот (Гц)
            amplitudes: массив амплитуд
            zone: зона состояния (A/B/C/D)
            rms_value: значение СКЗ
        """
        self.ax.clear()
        
        # Построение спектра
        self.ax.plot(frequencies, amplitudes, 'b-', linewidth=1.5, label='Спектр')
        
        # Границы зон ISO 10816
        zone_boundaries = [
            (2.3, 'orange', 'A/B'),
            (4.5, 'red', 'B/C'),
            (7.8, 'darkred', 'C/D')
        ]
        
        for threshold, color, label in zone_boundaries:
            self.ax.axhline(y=threshold, color=color, linestyle='--', 
                           linewidth=1, alpha=0.7, label=f'{label} ({threshold} мм/с)')
        
        # Подсветка текущей зоны
        zone_colors = {'A': 'green', 'B': 'orange', 'C': 'red', 'D': 'darkred'}
        zone_color = zone_colors.get(zone, 'gray')
        
        # Заполнение зоны
        if zone == 'A':
            self.ax.axhspan(0, 2.3, alpha=0.1, color='green')
        elif zone == 'B':
            self.ax.axhspan(0, 2.3, alpha=0.1, color='green')
            self.ax.axhspan(2.3, 4.5, alpha=0.1, color='orange')
        elif zone == 'C':
            self.ax.axhspan(0, 2.3, alpha=0.1, color='green')
            self.ax.axhspan(2.3, 4.5, alpha=0.1, color='orange')
            self.ax.axhspan(4.5, 7.8, alpha=0.1, color='red')
        else:
            self.ax.axhspan(0, 2.3, alpha=0.1, color='green')
            self.ax.axhspan(2.3, 4.5, alpha=0.1, color='orange')
            self.ax.axhspan(4.5, 7.8, alpha=0.1, color='red')
            self.ax.axhspan(7.8, max(8, max(amplitudes) * 1.1), alpha=0.1, color='darkred')
        
        # Настройки осей
        self.ax.set_xlabel('Частота, Гц', fontsize=10)
        self.ax.set_ylabel('Амплитуда, мм/с', fontsize=10)
        self.ax.set_title(f'Спектр вибрации | Зона {zone} | СКЗ: {rms_value:.3f} мм/с', 
                         fontsize=11)
        
        # Сетка
        self.ax.grid(True, alpha=0.3)
        
        # Легенда
        self.ax.legend(loc='upper right', fontsize=8)
        
        # Ограничение осей
        max_freq = max(frequencies) if len(frequencies) > 0 else 100
        max_amp = max(amplitudes) * 1.1 if len(amplitudes) > 0 else 10
        self.ax.set_xlim(0, max_freq)
        self.ax.set_ylim(0, max(max_amp, 10))
        
        self.draw()
    
    def plot_time_series(self, timestamps: np.ndarray, values: np.ndarray, 
                        sensor_name: str = ''):
        """
        Построение временного ряда
        
        Args:
            timestamps: массив временных меток
            values: массив значений
            sensor_name: имя датчика
        """
        self.ax.clear()
        
        self.ax.plot(timestamps, values, 'b-', linewidth=0.5)
        
        self.ax.set_xlabel('Время, с', fontsize=10)
        self.ax.set_ylabel('Виброскорость, мм/с', fontsize=10)
        self.ax.set_title(f'Временной ряд | {sensor_name}', fontsize=11)
        self.ax.grid(True, alpha=0.3)
        
        self.draw()
    
    def clear(self):
        """Очистка графика"""
        self.ax.clear()
        self.fig.text(0.5, 0.5, 'Загрузите данные для отображения',
                     ha='center', va='center', fontsize=12, alpha=0.5)
        self.draw()
