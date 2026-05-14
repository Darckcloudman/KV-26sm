"""Экран сырых данных с графиками для всех датчиков"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Dict, Optional

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rcParams

# Описание датчиков согласно обновлённой спецификации
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

# Настройка стилей matplotlib
rcParams['figure.facecolor'] = '#0a0a0a'
rcParams['axes.facecolor'] = '#1a1a1a'
rcParams['axes.edgecolor'] = '#333333'
rcParams['axes.labelcolor'] = '#e0e0e0'
rcParams['xtick.color'] = '#e0e0e0'
rcParams['ytick.color'] = '#e0e0e0'
rcParams['grid.color'] = '#333333'
rcParams['text.color'] = '#e0e0e0'


class RawDataCanvas(FigureCanvas):
    """Кастомный canvas для графиков сырых данных"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#1a1a1a')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.fig.patch.set_facecolor('#1a0a0a')
        
        # Настройка сетки для лучшей видимости
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#1a1a1a')
        
        # Установка стиля
        self._apply_style()
    
    def _apply_style(self):
        """Применение стилей к графику"""
        self.axes.tick_params(colors='#e0e0e0')
        for spine in self.axes.spines.values():
            spine.set_color('#333333')
    
    def plot_raw_signal(self, time_data: np.ndarray, signal_data: np.ndarray, 
                        sensor_id: int, sensor_name: str):
        """
        Отрисовка сырого сигнала
        
        Args:
            time_data: массив времени в секундах
            signal_data: массив виброускорения в м/с²
            sensor_id: номер датчика
            sensor_name: описание датчика
        """
        self.axes.clear()
        self._apply_style()
        
        # Децимация для большого количества точек
        if len(time_data) > 10000:
            step = len(time_data) // 10000
            time_data = time_data[::step]
            signal_data = signal_data[::step]
        
        # График сигнала
        self.axes.plot(time_data, signal_data, color='#ff69b4', linewidth=0.8, alpha=0.8)
        
        # Настройки осей
        self.axes.set_xlabel('Время (с)', fontsize=9)
        self.axes.set_ylabel('Ускорение (м/с²)', fontsize=9)
        self.axes.set_title(f'Датчик {sensor_id} -- {sensor_name}', fontsize=10, color='#ff69b4')
        
        # Сетка
        self.axes.grid(True, alpha=0.3, linestyle='--')
        
        # Автоподстройка
        self.axes.tick_params(labelsize=8)
        self.fig.tight_layout()
        
        self.draw()
    
    def show_no_data(self, sensor_id: int):
        """Отрисовка сообщения об отсутствии данных"""
        self.axes.clear()
        self._apply_style()
        
        self.axes.text(0.5, 0.5, f'Нет данных\nдля датчика {sensor_id}',
                       ha='center', va='center', fontsize=11, color='#666666')
        self.axes.set_xlim(0, 1)
        self.axes.set_ylim(0, 1)
        self.axes.axis('off')
        
        self.draw()


class RawDataScreen(QWidget):
    """Экран сырых данных"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sensor_data: Dict[int, dict] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel("[=] СЫРЫЕ ДАННЫЕ [ТЕКСТОМ] [=]")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #ff69b4;
            padding: 15px;
            border-bottom: 2px solid #333333;
        """)
        layout.addWidget(title_label)
        
        # Скроллящаяся область для графиков
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #333333;
                background-color: #0a0a0a;
                border-radius: 5px;
            }
        """)
        
        content_widget = QWidget()
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        content_widget.setLayout(grid_layout)
        
        # Создаём 8 панелей для датчиков (2 колонки x 4 строки)
        self.canvas_widgets: Dict[int, QWidget] = {}
        
        for sensor_id in range(1, 9):
            row = (sensor_id - 1) // 2
            col = (sensor_id - 1) % 2
            
            # Контейнер для панели датчика
            panel = QFrame()
            panel.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 2px solid #333333;
                    border-radius: 8px;
                }
            """)
            
            panel_layout = QVBoxLayout()
            panel_layout.setContentsMargins(10, 10, 10, 10)
            
            # Заголовок панели
            desc = SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}")
            header = QLabel(f"[{sensor_id:02d}] {desc}")
            header.setStyleSheet("""
                font-size: 12px;
                font-weight: bold;
                color: #ff69b4;
                padding: 8px;
                background-color: #0a0a0a;
                border-radius: 4px;
            """)
            header.setWordWrap(True)
            panel_layout.addWidget(header)
            
            # Canvas для графика
            canvas = RawDataCanvas(self, width=5, height=3, dpi=80)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            panel_layout.addWidget(canvas)
            
            panel.setLayout(panel_layout)
            
            grid_layout.addWidget(panel, row, col)
            self.canvas_widgets[sensor_id] = canvas
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("<- Назад к информации")
        self.btn_back.setFixedWidth(200)
        self.btn_back.clicked.connect(self._on_back)
        btn_layout.addWidget(self.btn_back)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def set_sensor_data(self, sensor_data: Dict[int, dict]):
        """
        Установка данных датчиков
        
        Args:
            sensor_data: словарь {sensor_id: {'time': time_array, 'signal': signal_array, 'name': sensor_name}}
        """
        self._sensor_data = sensor_data
        
        # Обновляем графики
        for sensor_id in range(1, 9):
            canvas = self.canvas_widgets[sensor_id]
            
            if sensor_id in sensor_data:
                data = sensor_data[sensor_id]
                time_data = data.get('time', np.array([]))
                signal_data = data.get('signal', np.array([]))
                sensor_name = data.get('name', SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}"))
                
                if len(time_data) > 0 and len(signal_data) > 0:
                    canvas.plot_raw_signal(time_data, signal_data, sensor_id, sensor_name)
                else:
                    canvas.show_no_data(sensor_id)
            else:
                canvas.show_no_data(sensor_id)
    
    def _on_back(self):
        """Обработка нажатия кнопки назад"""
        if hasattr(self, '_on_back_callback'):
            self._on_back_callback()
    
    def set_back_callback(self, callback):
        """Установка callback для кнопки назад"""
        self._on_back_callback = callback
