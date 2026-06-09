# -*- coding: utf-8 -*-
"""
Экран информации о загрузке файлов v1.4.3
- Название ВЭУ без префикса "ВЭУ:"
- Селектор датчиков с подсветкой статусов
- 3D график ВЧ(ф) слева
- Статистика записей справа
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPainter, QPen, QColor, QLinearGradient
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from ..dal.config import settings
from ..dal.repositories.base import IVibrationRepository
from .workers.statistics_worker import StatisticsWorker
from .workers.spectrum_worker import SpectrumDataWorker
from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY, COLOR_BG_DARK,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_BORDER,
    FONT_FAMILY, FONT_FAMILY_MONO,
    BUTTON_STYLE
)


# Описание датчиков
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


class SensorSelector(QFrame):
    """Панель выбора датчика с 8 кнопками (разделены на группы) с подсветкой статуса."""
    
    sensor_selected = Signal(int)
    
    # Цвета статусов
    STATUS_COMPLETE = "#00C853"  # Зелёный - полностью загружен
    STATUS_PARTIAL = "#FFC107"   # Оранжевый - частично загружен
    STATUS_MISSING = "#DD2C00"   # Красный - отсутствует
    
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
        self.sensor_status = {}
        
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
            self._update_button_style(btn, sensor_id)
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
            self._update_button_style(btn, sensor_id)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, sid=sensor_id: self._on_sensor_clicked(sid))
            generator_layout.addWidget(btn)
            self.buttons[sensor_id] = btn
        
        main_layout.addLayout(generator_layout)
        self.buttons[1].setChecked(True)
    
    def _update_button_style(self, btn: QPushButton, sensor_id: int):
        """Обновить стиль кнопки в зависимости от статуса."""
        status = self.sensor_status.get(sensor_id, self.STATUS_MISSING)
        
        if self.selected_sensor == sensor_id:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {status};
                    color: {COLOR_BG_PRIMARY};
                    border: 2px solid {status};
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_ACCENT_HOVER};
                    border: 2px solid {COLOR_ACCENT};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BG_SECONDARY};
                    color: {status};
                    border: 1px solid {status};
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_TERTIARY};
                    color: {COLOR_TEXT_PRIMARY};
                    border: 1px solid {COLOR_TEXT_PRIMARY};
                }}
            """)
    
    def update_sensor_status(self, sensor_id: int, status: str):
        """Обновить статус датчика."""
        self.sensor_status[sensor_id] = status
        if sensor_id in self.buttons:
            self._update_button_style(self.buttons[sensor_id], sensor_id)
    
    def set_all_statuses(self, statuses: Dict[int, str]):
        """Установить статусы всех датчиков."""
        self.sensor_status = statuses
        for sensor_id, btn in self.buttons.items():
            self._update_button_style(btn, sensor_id)
    
    def _on_sensor_clicked(self, sensor_id: int):
        self.selected_sensor = sensor_id
        for sid, btn in self.buttons.items():
            btn.setChecked(sid == sensor_id)
            self._update_button_style(btn, sid)
        self.sensor_selected.emit(sensor_id)
    
    def set_selected(self, sensor_id: int):
        if sensor_id in self.buttons:
            self.buttons[sensor_id].setChecked(True)
            self._on_sensor_clicked(sensor_id)


class Spectrum3DChart(QWidget):
    """3D спектральный график (дата, Гц, мм/с²)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.data_points = []
        self.sensor_id = 1
        self.sensor_name = ""
    
    def set_data(self, data_points: List[tuple], sensor_id: int, sensor_name: str):
        self.data_points = data_points
        self.sensor_id = sensor_id
        self.sensor_name = sensor_name
        self.update()
    
    def show_no_data(self, sensor_id: int):
        self.data_points = []
        self.sensor_id = sensor_id
        self.update()
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))
            
            if not self.data_points:
                painter.setPen(QColor(COLOR_TEXT_PRIMARY))
                painter.setFont(QFont(FONT_FAMILY_MONO, 12, QFont.Weight.Bold))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Нет данных\nдля датчика {self.sensor_id}')
                return
            
            dates = [p[0] for p in self.data_points]
            freqs = [p[1] for p in self.data_points]
            amps = [p[2] for p in self.data_points]
            
            min_date, max_date = min(dates), max(dates)
            min_freq, max_freq = min(freqs), max(freqs)
            max_amp = max(amps) * 1.1 if amps else 1.0
            
            m_left, m_right, m_top, m_bottom = 60, 20, 20, 50
            w, h = self.width(), self.height()
            plot_w, plot_h = w - m_left - m_right, h - m_top - m_bottom
            
            if plot_w <= 0 or plot_h <= 0: return
            
            def date_to_x(dt):
                total = (max_date - min_date).total_seconds() or 1
                return m_left + ((dt - min_date).total_seconds() / total) * plot_w
            
            def freq_to_y(f):
                rng = (max_freq - min_freq) or 1
                return m_top + plot_h - ((f - min_freq) / rng) * plot_h
            
            def amp_to_size(a):
                return max(2, min(10, (a / max_amp) * 10)) if max_amp > 0 else 3
            
            painter.setPen(QPen(QColor(COLOR_ACCENT), 2))
            painter.drawLine(m_left, m_top, m_left, m_top + plot_h)
            painter.drawLine(m_left, m_top + plot_h, m_left + plot_w, m_top + plot_h)
            
            for dt, freq, amp in self.data_points[:500]:  # Оптимизация
                x, y = date_to_x(dt), freq_to_y(freq)
                r = amp_to_size(amp)
                ratio = amp / max_amp if max_amp > 0 else 0.5
                color = QColor(int(255 * ratio), int(255 * (1 - ratio)), 0)
                painter.setPen(QPen(color, 1))
                painter.setBrush(color)
                painter.drawEllipse(int(x - r/2), int(y - r/2), int(r), int(r))
            
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Weight.Bold))
            painter.drawText(m_left, 15, f'Датчик {self.sensor_id} — {self.sensor_name}')
            painter.setPen(QColor(COLOR_TEXT_TERTIARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 8))
            painter.drawText(w // 2 - 40, h - 10, 'Дата')
            painter.drawText(5, h // 2, 'Гц')
        except Exception as e:
            painter = QPainter(self)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Ошибка:\n{str(e)}')


class RecordsChart(QWidget):
    """2D график количества записей по дням."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.records_by_date = {}
        self.turbine_name = ""
    
    def set_data(self, records_by_date: Dict[datetime.date, int], turbine_name: str):
        self.records_by_date = records_by_date
        self.turbine_name = turbine_name
        self.update()
    
    def show_no_data(self):
        self.records_by_date = {}
        self.update()
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))
            
            if not self.records_by_date:
                painter.setPen(QColor(COLOR_TEXT_PRIMARY))
                painter.setFont(QFont(FONT_FAMILY_MONO, 12, QFont.Weight.Bold))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Нет данных\nпо записям')
                return
            
            sorted_dates = sorted(self.records_by_date.keys())
            counts = [self.records_by_date[d] for d in sorted_dates]
            min_date, max_date = sorted_dates[0], sorted_dates[-1]
            max_count = max(counts) * 1.1 if counts else 1.0
            
            m_left, m_right, m_top, m_bottom = 60, 20, 20, 50
            w, h = self.width(), self.height()
            plot_w, plot_h = w - m_left - m_right, h - m_top - m_bottom
            bar_width = max(2, plot_w / len(sorted_dates) - 2)
            
            def date_to_x(dt):
                total = (max_date - min_date).days or 1
                return m_left + ((dt - min_date).days / total) * plot_w
            
            def count_to_y(c):
                return m_top + plot_h - (c / max_count) * plot_h if max_count > 0 else m_top + plot_h
            
            painter.setPen(QPen(QColor(COLOR_ACCENT), 2))
            painter.drawLine(m_left, m_top, m_left, m_top + plot_h)
            painter.drawLine(m_left, m_top + plot_h, m_left + plot_w, m_top + plot_h)
            
            gradient = QLinearGradient(0, m_top, 0, m_top + plot_h)
            gradient.setColorAt(0, QColor(COLOR_ACCENT))
            gradient.setColorAt(1, QColor(COLOR_ACCENT_HOVER))
            
            for dt in sorted_dates:
                x = date_to_x(dt) - bar_width / 2
                y = count_to_y(self.records_by_date[dt])
                painter.setPen(QPen(COLOR_ACCENT, 1))
                painter.setBrush(gradient)
                painter.drawRect(int(x), int(y), int(bar_width), int(m_top + plot_h - y))
            
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Weight.Bold))
            painter.drawText(m_left, 15, f'Статистика: {self.turbine_name}')
            painter.setPen(QColor(COLOR_TEXT_TERTIARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 8))
            painter.drawText(w // 2 - 40, h - 10, 'Дата')
            painter.drawText(5, h // 2, 'Записей')
        except Exception as e:
            painter = QPainter(self)
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Ошибка:\n{str(e)}')
