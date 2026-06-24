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
    """3D спектральный график (каскад спектров по датам)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border: 1px solid {COLOR_BORDER}; border-radius: 4px;")
        self.spectrum_data = {}  # {date: [(freq, amp), ...]}
        self.sensor_id = 1
        self.sensor_name = ""
    
    def set_data(self, data_points: List[dict], sensor_id: int, sensor_name: str):
        """
        Установить данные спектра.
        
        Args:
            data_points: Список {'timestamp': datetime, 'frequency': float, 'amplitude': float}
            sensor_id: Номер датчика
            sensor_name: Название датчика
        """
        self.sensor_id = sensor_id
        self.sensor_name = sensor_name
        
        # Группируем по датам
        from collections import defaultdict
        self.spectrum_data = defaultdict(list)
        
        for point in data_points:
            if point['timestamp'] and point['frequency'] and point['amplitude']:
                date_key = point['timestamp'].date()
                self.spectrum_data[date_key].append((
                    point['frequency'],
                    point['amplitude']
                ))
        
        # Сортируем частоты внутри каждой даты
        for date in self.spectrum_data:
            self.spectrum_data[date].sort(key=lambda x: x[0])
        
        self.update()
    
    def show_no_data(self, sensor_id: int):
        self.spectrum_data = {}
        self.sensor_id = sensor_id
        self.update()
    
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))
            
            if not self.spectrum_data:
                painter.setPen(QColor(COLOR_TEXT_PRIMARY))
                painter.setFont(QFont(FONT_FAMILY_MONO, 12, QFont.Weight.Bold))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f'Нет данных\nдля датчика {self.sensor_id}')
                return
            
            # Параметры отрисовки
            m_left, m_right, m_top, m_bottom = 70, 30, 30, 50
            w, h = self.width(), self.height()
            plot_w, plot_h = w - m_left - m_right, h - m_top - m_bottom
            
            if plot_w <= 0 or plot_h <= 0:
                return
            
            # Получаем все даты и сортируем
            sorted_dates = sorted(self.spectrum_data.keys())
            num_dates = len(sorted_dates)
            
            # Находим общий диапазон частот
            all_freqs = []
            all_amps = []
            for freq, amp in [p for points in self.spectrum_data.values() for p in points]:
                all_freqs.append(freq)
                all_amps.append(amp)
            
            if not all_freqs:
                return
            
            min_freq, max_freq = min(all_freqs), max(all_freqs)
            max_amp = max(all_amps) * 1.1 if all_amps else 1.0
            
            # Шаг по оси Y для каждого спектра
            spectrum_spacing = plot_h / (num_dates + 1)
            
            # Рисуем оси
            painter.setPen(QPen(QColor(COLOR_TEXT_TERTIARY), 1))
            painter.drawLine(m_left, m_top, m_left, m_top + plot_h)  # Y ось
            painter.drawLine(m_left, m_top + plot_h, m_left + plot_w, m_top + plot_h)  # X ось
            
            # Рисуем подписи осей
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 9, QFont.Weight.Bold))
            painter.drawText(5, m_top + plot_h // 2, 'Гц')
            painter.drawText(w // 2, h - 10, 'Частота, Гц')
            
            # Подписи частот
            painter.setPen(QColor(COLOR_TEXT_TERTIARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 7))
            for i in range(5):
                freq = min_freq + (max_freq - min_freq) * i / 4
                y = m_top + plot_h - (i / 4) * plot_h
                painter.drawText(5, int(y + 3), f'{freq:.0f}')
            
            # Рисуем каждый спектр
            colors = [
                QColor("#FF0000"),  # Красный
                QColor("#FF7F00"),  # Оранжевый
                QColor("#FFFF00"),  # Жёлтый
                QColor("#00FF00"),  # Зелёный
                QColor("#0000FF"),  # Синий
                QColor("#4B0082"),  # Индиго
                QColor("#9400D3"),  # Фиолетовый
            ]
            
            for idx, date in enumerate(sorted_dates):
                points = self.spectrum_data[date]
                if not points:
                    continue
                
                # Базовая линия для этого спектра
                base_y = m_top + plot_h - (idx + 1) * spectrum_spacing
                
                # Цвет спектра
                color = colors[idx % len(colors)]
                painter.setPen(QPen(color, 1))
                
                # Рисуем линию спектра
                first_point = True
                for freq, amp in points:
                    # Нормализуем частоту по X
                    if max_freq > min_freq:
                        x = m_left + ((freq - min_freq) / (max_freq - min_freq)) * plot_w
                    else:
                        x = m_left + plot_w / 2
                    
                    # Амплитуда по Y (от базовой линии)
                    amp_height = (amp / max_amp) * (spectrum_spacing * 0.8)
                    y = base_y - amp_height
                    
                    if first_point:
                        painter.drawLine(int(x), int(base_y), int(x), int(y))
                        first_point = False
                    else:
                        painter.drawLine(int(x), int(base_y), int(x), int(y))
                
                # Подпись даты
                painter.setPen(QColor(COLOR_TEXT_SECONDARY))
                painter.setFont(QFont(FONT_FAMILY_MONO, 7))
                date_str = date.strftime("%d.%m.%Y")
                painter.drawText(2, int(base_y + 3), date_str)
            
            # Заголовок
            painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            painter.setFont(QFont(FONT_FAMILY_MONO, 10, QFont.Weight.Bold))
            painter.drawText(m_left, 15, f'Датчик {self.sensor_id} — {self.sensor_name}')
            
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


class UploadInfoScreen(QWidget):
    """Экран информации о загрузке v1.4.3"""
    
    def __init__(self, repository = None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._loaded_sensors = {}
        self._sensor_files = {}
        self._turbine_name = "Неизвестная ВЭУ"
        self._current_sensor = 1
        self._spectrum_data = []
        self._records_by_date = {}
        self._statistics_worker = None
        self._spectrum_worker = None
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 20, 30, 20)
        
        title_label = QLabel("ИНФОРМАЦИЯ О ЗАГРУЗКЕ")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLOR_TEXT_PRIMARY}; padding: 15px; border-bottom: 2px solid {COLOR_BORDER};")
        layout.addWidget(title_label)
        
        top_panel = QHBoxLayout()
        top_panel.setSpacing(15)
        
        self.turbine_label = QLabel("WTG56")
        self.turbine_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLOR_TEXT_PRIMARY}; padding: 10px; background-color: {COLOR_BG_SECONDARY}; border-radius: 5px; min-width: 150px;")
        top_panel.addWidget(self.turbine_label)
        
        self.params_label = QLabel("")
        self.params_label.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_SECONDARY}; padding: 10px; background-color: {COLOR_BG_TERTIARY}; border: 1px solid {COLOR_BORDER}; border-radius: 5px;")
        self.params_label.setWordWrap(True)
        top_panel.addWidget(self.params_label, stretch=1)
        
        self.sensor_selector = SensorSelector(self)
        self.sensor_selector.sensor_selected.connect(self._on_sensor_selected)
        top_panel.addWidget(self.sensor_selector)
        layout.addLayout(top_panel)
        
        charts_panel = QHBoxLayout()
        charts_panel.setSpacing(15)
        
        left_panel = QVBoxLayout()
        left_label = QLabel("ВЧ(ф) СПЕКТР (3D)")
        left_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLOR_TEXT_PRIMARY}; padding: 5px;")
        left_panel.addWidget(left_label)
        self.spectrum_chart = Spectrum3DChart(self)
        self.spectrum_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_panel.addWidget(self.spectrum_chart, stretch=1)
        charts_panel.addLayout(left_panel, stretch=1)
        
        right_panel = QVBoxLayout()
        right_label = QLabel("КОЛИЧЕСТВО ЗАПИСЕЙ (4 месяца)")
        right_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLOR_TEXT_PRIMARY}; padding: 5px;")
        right_panel.addWidget(right_label)
        self.records_chart = RecordsChart(self)
        self.records_chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_panel.addWidget(self.records_chart, stretch=1)
        charts_panel.addLayout(right_panel, stretch=1)
        
        layout.addLayout(charts_panel)
        
        btn_layout = QHBoxLayout()
        self.btn_back = QPushButton("<- Назад к выбору")
        self.btn_back.setFixedWidth(180)
        self.btn_back.setStyleSheet(BUTTON_STYLE)
        self.btn_back.clicked.connect(self._on_back)
        btn_layout.addWidget(self.btn_back)
        
        self.btn_process = QPushButton("[>] Обработать")
        self.btn_process.setFixedWidth(180)
        self.btn_process.setStyleSheet(BUTTON_STYLE)
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self._on_process)
        btn_layout.addWidget(self.btn_process)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _on_sensor_selected(self, sensor_id: int):
        self._current_sensor = sensor_id
        self._load_spectrum_data()
    
    def _load_spectrum_data(self, months: int = 10):
        if not settings.use_database or not self.repository:
            self.spectrum_chart.show_no_data(self._current_sensor)
            return
        if self._spectrum_worker and self._spectrum_worker.isRunning():
            self._spectrum_worker.terminate()
        # Используем диапазон 300 дней (~10 месяцев) для охвата тестовых данных
        # Данные за сентябрь 2025, сейчас июнь 2026 (~290 дней назад)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)
        self._spectrum_worker = SpectrumDataWorker(self.repository, self._turbine_name, self._current_sensor, months=months, parent=self)
        self._spectrum_worker.data_ready.connect(self._on_spectrum_loaded)
        self._spectrum_worker.error.connect(self._on_spectrum_error)
        self._spectrum_worker.start()
    
    def _on_spectrum_loaded(self, data_points):
        """
        Обработать данные спектра.
        
        Args:
            data_points: Список dict {'timestamp': datetime, 'frequency': float, 'amplitude': float}
        """
        self._spectrum_data = data_points
        sensor_name = SENSOR_DESCRIPTIONS.get(self._current_sensor, f"Датчик {self._current_sensor}")
        self.spectrum_chart.set_data(data_points, self._current_sensor, sensor_name)
    
    def _on_spectrum_error(self, error_msg: str):
        self.spectrum_chart.show_no_data(self._current_sensor)
    
    def set_upload_data(self, turbine_name: str, loaded_sensors, sensor_files = None, generator_speed = "", active_power = "", record_length = "", record_number = "", record_datetime = ""):
        self._turbine_name = turbine_name
        self._loaded_sensors = loaded_sensors
        self._sensor_files = sensor_files or {}
        self.turbine_label.setText(f"{turbine_name}")
        
        params_parts = []
        if generator_speed: params_parts.append(f"Скорость генератора: {generator_speed}")
        if active_power: params_parts.append(f"Активная мощность: {active_power}")
        if record_length: params_parts.append(f"Длина записи: {record_length}")
        if record_number: params_parts.append(f"№ записи: {record_number}")
        if record_datetime: params_parts.append(f"Дата: {record_datetime}")
        self.params_label.setText(" | ".join(params_parts) if params_parts else "Параметры не определены")
        
        self._update_sensor_statuses()
        self.btn_process.setEnabled(len(loaded_sensors) > 0)
        
        if settings.use_database and self.repository:
            # Используем 14 месяцев для охвата тестовых данных (сентябрь 2025 - январь 2026)
            self._load_statistics(turbine_name, months=14)
    
    def _update_sensor_statuses(self):
        statuses = {}
        for sensor_id in range(1, 9):
            if sensor_id not in self._loaded_sensors:
                statuses[sensor_id] = SensorSelector.STATUS_MISSING
            else:
                files = self._sensor_files.get(sensor_id, {})
                has_all = 'FILTER' in files and 'HIGH' in files and 'LOW' in files
                statuses[sensor_id] = SensorSelector.STATUS_COMPLETE if has_all else SensorSelector.STATUS_PARTIAL
        self.sensor_selector.set_all_statuses(statuses)
    
    def _load_statistics(self, wtg_id: str, months: int = 14):
        if self._statistics_worker and self._statistics_worker.isRunning():
            self._statistics_worker.terminate()
        # Используем 10 месяцев (300 дней) для охвата тестовых данных
        # Данные за сентябрь 2025, сейчас июнь 2026 (~290 дней назад)
        self._statistics_worker = StatisticsWorker(self.repository, wtg_id, months=10, parent=self)
        self._statistics_worker.statistics_ready.connect(self._on_statistics_loaded)
        self._statistics_worker.error.connect(self._on_statistics_error)
        self._statistics_worker.start()
    
    def _on_statistics_loaded(self, stats):
        if stats and 'records_timeline' in stats:
            timeline = stats['records_timeline']
            self._records_by_date = {}
            for date_str, count in timeline.items():
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                    self._records_by_date[dt] = count
                except: pass
            self.records_chart.set_data(self._records_by_date, self._turbine_name)
        self._load_spectrum_data()
    
    def _on_statistics_error(self, error_msg: str):
        self.records_chart.show_no_data()
        self.spectrum_chart.show_no_data(self._current_sensor)
    
    def get_loaded_sensors(self):
        return self._loaded_sensors.copy()
    
    def _on_back(self):
        if hasattr(self, '_on_back_callback'):
            self._on_back_callback()
    
    def _on_process(self):
        if hasattr(self, '_on_process_callback'):
            self._on_process_callback()
    
    def set_callbacks(self, on_back=None, on_process=None):
        if on_back: self._on_back_callback = on_back
        if on_process: self._on_process_callback = on_process
