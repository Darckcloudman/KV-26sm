"""Экран информации о загрузке файлов"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFont
from typing import Dict, List, Optional
from pathlib import Path

from ..dal.config import settings
from ..dal.repositories.base import IVibrationRepository
from .workers.statistics_worker import StatisticsWorker
from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_ACCENT, COLOR_BORDER, BUTTON_STYLE
)


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


class UploadInfoScreen(QWidget):
    """Экран информации о загрузке"""
    
    def __init__(self, repository: IVibrationRepository = None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._loaded_sensors: Dict[int, dict] = {}  # sensor_id -> result
        self._sensor_files: Dict[int, Dict[str, str]] = {}  # sensor_id -> {file_type: filepath}
        self._turbine_name: str = "Неизвестная ВЭУ"
        self._generator_speed: str = ""
        self._active_power: str = ""
        self._record_length: str = ""
        self._record_number: str = ""
        self._record_datetime: str = ""
        self._statistics_worker: Optional[StatisticsWorker] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        title_label = QLabel("ИНФОРМАЦИЯ О ЗАГРУЗКЕ")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLOR_TEXT_PRIMARY};
            padding: 15px;
            border-bottom: 2px solid {COLOR_BORDER};
        """)
        layout.addWidget(title_label)
        
        # Информация о ВЭУ и параметрах записи
        self.turbine_label = QLabel("ВЭУ: Неизвестная")
        self.turbine_label.setStyleSheet(f"""
            font-size: 16px;
            color: {COLOR_TEXT_PRIMARY};
            padding: 10px;
            background-color: {COLOR_BG_SECONDARY};
            border-radius: 5px;
        """)
        layout.addWidget(self.turbine_label)
        
        # Параметры записи
        self.params_label = QLabel("")
        self.params_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLOR_TEXT_SECONDARY};
            padding: 10px;
            background-color: {COLOR_BG_TERTIARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: 5px;
        """)
        self.params_label.setWordWrap(True)
        layout.addWidget(self.params_label)
        
        # Блок статистики из БД (только если USE_DATABASE=true)
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 5px;
            }}
        """)
        self.stats_frame.setVisible(False)
        
        stats_layout = QVBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(15, 15, 15, 15)
        stats_layout.setSpacing(10)
        
        stats_title = QLabel("Статистика по ВЭУ (из БД)")
        stats_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLOR_TEXT_PRIMARY};
        """)
        stats_layout.addWidget(stats_title)
        
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(10)
        
        # Метки для статистики
        self.stat_total_label = self._create_stat_label("Всего записей:", "—")
        self.stat_first_label = self._create_stat_label("Первая запись:", "—")
        self.stat_last_label = self._create_stat_label("Последняя запись:", "—")
        self.stat_critical_label = self._create_stat_label("Критических (зона D):", "—")
        self.stat_avg_rms_label = self._create_stat_label("Средний RMS (датчик 1):", "—")
        
        self.stats_grid.addWidget(self.stat_total_label, 0, 0)
        self.stats_grid.addWidget(self.stat_first_label, 0, 1)
        self.stats_grid.addWidget(self.stat_last_label, 1, 0)
        self.stats_grid.addWidget(self.stat_critical_label, 1, 1)
        self.stats_grid.addWidget(self.stat_avg_rms_label, 2, 0)
        
        stats_layout.addLayout(self.stats_grid)
        
        # Статус загрузки
        self.stats_status = QLabel("")
        self.stats_status.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 11px;")
        stats_layout.addWidget(self.stats_status)
        
        layout.addWidget(self.stats_frame)
        
        # Счётчик датчиков
        self.counter_label = QLabel("")
        self.counter_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLOR_TEXT_SECONDARY};
            padding: 10px;
            font-weight: bold;
        """)
        layout.addWidget(self.counter_label)
        
        # Список датчиков
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {COLOR_BORDER};
                background-color: {COLOR_BG_TERTIARY};
                border-radius: 5px;
            }}
        """)
        
        sensors_widget = QWidget()
        self.sensors_layout = QVBoxLayout()
        self.sensors_layout.setSpacing(10)
        sensors_widget.setLayout(self.sensors_layout)
        
        scroll.setWidget(sensors_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Кнопки
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
    
    def _create_stat_label(self, title: str, value: str) -> QLabel:
        """Создать метку статистики."""
        label = QLabel(f"<b>{title}</b> {value}")
        label.setStyleSheet(f"""
            color: {COLOR_TEXT_SECONDARY};
            font-size: 12px;
            padding: 5px;
            background-color: {COLOR_BG_TERTIARY};
            border-radius: 3px;
        """)
        return label
    
    def set_upload_data(self, turbine_name: str, loaded_sensors: Dict[int, dict],
                       sensor_files: Dict[int, Dict[str, str]] = None,
                       generator_speed: str = "", active_power: str = "", 
                       record_length: str = "", record_number: str = "", record_datetime: str = ""):
        """
        Установка данных о загрузке
        
        Args:
            turbine_name: название ветротурбины
            loaded_sensors: словарь загруженных датчиков {sensor_id: result}
            sensor_files: словарь файлов по датчикам {sensor_id: {file_type: filepath}}
            generator_speed: скорость генератора (например, "1123 RPM")
            active_power: активная мощность (например, "2334 KW")
            record_length: длина записи (например, "64 s")
            record_number: номер записи (первые 5 цифр)
            record_datetime: дата и время записи
        """
        self._turbine_name = turbine_name
        self._loaded_sensors = loaded_sensors
        self._sensor_files = sensor_files or {}
        self._generator_speed = generator_speed
        self._active_power = active_power
        self._record_length = record_length
        self._record_number = record_number
        self._record_datetime = record_datetime
        self._update_display()
    
        # Загружаем статистику из БД
        self._load_statistics(turbine_name)
    
    def _load_statistics(self, wtg_id: str):
        """Загрузить статистику по ВЭУ из БД."""
        # Проверяем, используется ли БД
        if not settings.use_database or not self.repository:
            self.stats_frame.setVisible(False)
            return
        
        # Показываем статус загрузки
        self.stats_frame.setVisible(True)
        self.stats_status.setText("Загрузка статистики...")
        
        # Останавливаем предыдущий воркер
        if self._statistics_worker and self._statistics_worker.isRunning():
            self._statistics_worker.terminate()
        
        # Создаём и запускаем воркер
        self._statistics_worker = StatisticsWorker(self.repository, wtg_id, self)
        self._statistics_worker.statistics_ready.connect(self._on_statistics_loaded)
        self._statistics_worker.error.connect(self._on_statistics_error)
        self._statistics_worker.start()
    
    def _on_statistics_loaded(self, stats: Optional[Dict]):
        """Обработка загрузки статистики."""
        if stats is None:
            self.stats_status.setText("Нет данных в БД для этой ВЭУ")
            return
        
        # Форматируем и отображаем
        total = stats.get('total_archives', 0)
        first_record = stats.get('first_record')
        last_record = stats.get('last_record')
        critical_count = stats.get('critical_count', 0)
        avg_rms_per_sensor = stats.get('avg_rms_per_sensor', {})
        
        # Форматируем даты
        first_str = first_record.strftime("%d.%m.%Y %H:%M") if first_record else "—"
        last_str = last_record.strftime("%d.%m.%Y %H:%M") if last_record else "—"
        
        # Средний RMS датчика 1
        avg_rms_1 = avg_rms_per_sensor.get(1, 0.0)
        avg_rms_str = f"{avg_rms_1:.2f} мм/с" if avg_rms_1 else "—"
        
        # Обновляем метки
        self.stat_total_label.setText(f"<b>Всего записей:</b> {total}")
        self.stat_first_label.setText(f"<b>Первая запись:</b> {first_str}")
        self.stat_last_label.setText(f"<b>Последняя запись:</b> {last_str}")
        
        # Критические с цветом
        crit_color = "#DD2C00" if critical_count > 0 else "#00C853"
        self.stat_critical_label.setText(
            f"<b>Критических (зона D):</b> <span style='color: {crit_color}; font-weight: bold;'>{critical_count}</span>"
        )
        
        # RMS с зоной
        zone = self._get_zone(avg_rms_1)
        zone_color = {"A": "#00C853", "B": "#FFC107", "C": "#FF9800", "D": "#DD2C00"}.get(zone, "#FFFFFF")
        self.stat_avg_rms_label.setText(
            f"<b>Средний RMS (датчик 1):</b> <span style='color: {zone_color}; font-weight: bold;'>{avg_rms_str}</span> (зона {zone})"
        )
        
        self.stats_status.setText("Статистика загружена")
    
    def _on_statistics_error(self, error_msg: str):
        """Обработка ошибки загрузки статистики."""
        self.stats_status.setText(f"Ошибка: {error_msg}")
    
    def _get_zone(self, rms: float) -> str:
        """Определить зону по RMS."""
        if rms < 2.3:
            return "A"
        elif rms < 4.5:
            return "B"
        elif rms < 7.8:
            return "C"
        else:
            return "D"
    
    def _update_display(self):
        """Обновление отображения"""
        # Обновляем название ВЭУ
        self.turbine_label.setText(f"ВЭУ: {self._turbine_name}")
        
        # Обновляем параметры записи
        params_parts = []
        if self._generator_speed:
            params_parts.append(f"Скорость генератора: {self._generator_speed}")
        if self._active_power:
            params_parts.append(f"Активная мощность: {self._active_power}")
        if self._record_length:
            params_parts.append(f"Длина записи: {self._record_length}")
        if self._record_number:
            params_parts.append(f"Номер записи: {self._record_number}")
        if self._record_datetime:
            params_parts.append(f"Дата/время: {self._record_datetime}")
        
        params_text = "\n".join(params_parts) if params_parts else "Параметры не определены"
        self.params_label.setText(params_text)
        
        # Определяем загруженные и отсутствующие датчики
        loaded_ids = sorted(self._loaded_sensors.keys())
        all_ids = set(range(1, 9))
        missing_ids = sorted(all_ids - set(loaded_ids))
        
        # Проверяем полноту файлов для каждого датчика
        complete_sensors = []
        incomplete_sensors = []
        
        for sensor_id in loaded_ids:
            files = self._sensor_files.get(sensor_id, {})
            has_filter = 'FILTER' in files
            has_high = 'HIGH' in files
            has_low = 'LOW' in files
            
            if has_filter and has_high and has_low:
                complete_sensors.append(sensor_id)
            else:
                incomplete_sensors.append(sensor_id)
        
        # Обновляем счётчик
        if len(loaded_ids) == 8 and len(incomplete_sensors) == 0:
            self.counter_label.setText("[+] Все датчики загружены полностью (по 3 файла каждый)")
            self.counter_label.setStyleSheet("""
                font-size: 14px;
                color: #00ff00;
                padding: 10px;
                font-weight: bold;
            """)
        elif len(loaded_ids) == 8:
            self.counter_label.setText(
                f"[!] Все 8 датчиков загружены, но {len(incomplete_sensors)} имеют неполный набор файлов"
            )
            self.counter_label.setStyleSheet("""
                font-size: 14px;
                color: #ffa500;
                padding: 10px;
                font-weight: bold;
            """)
        else:
            missing_str = ", ".join(map(str, missing_ids)) if missing_ids else "нет"
            self.counter_label.setText(
                f"Загружено: {len(loaded_ids)} из 8. Отсутствуют датчики: {missing_str}"
            )
            self.counter_label.setStyleSheet("""
                font-size: 14px;
                color: #ffa500;
                padding: 10px;
                font-weight: bold;
            """)
        
        # Обновляем список датчиков
        for i in range(self.sensors_layout.count()):
            widget = self.sensors_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for sensor_id in range(1, 9):
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 1px solid #333333;
                    border-radius: 5px;
                }
            """)
            
            frame_layout = QHBoxLayout()
            
            # Статус и полнота файлов
            if sensor_id in self._loaded_sensors:
                files = self._sensor_files.get(sensor_id, {})
                has_filter = 'FILTER' in files
                has_high = 'HIGH' in files
                has_low = 'LOW' in files
                
                if has_filter and has_high and has_low:
                    status = "[OK]"
                    status_color = "#00ff00"
                else:
                    missing = []
                    if not has_filter: missing.append("FILTER")
                    if not has_high: missing.append("HIGH")
                    if not has_low: missing.append("LOW")
                    status = f"[~] {', '.join(missing)}"
                    status_color = "#ffa500"
            else:
                status = "[-]"
                status_color = "#ff0000"
            
            status_label = QLabel(status)
            status_label.setStyleSheet(f"font-size: 12px; color: {status_color}; font-weight: bold;")
            frame_layout.addWidget(status_label)
            
            # Номер и описание
            desc = SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}")
            info_label = QLabel(f"Датчик {sensor_id} -- {desc}")
            info_label.setStyleSheet("font-size: 13px; color: #e0e0e0;")
            frame_layout.addWidget(info_label, stretch=1)
            
            frame.setLayout(frame_layout)
            self.sensors_layout.addWidget(frame)
        
        # Активируем кнопку обработки если есть хотя бы один датчик
        self.btn_process.setEnabled(len(loaded_ids) > 0)
    
    def get_loaded_sensors(self) -> Dict[int, dict]:
        """Возвращает загруженные датчики"""
        return self._loaded_sensors.copy()
    
    def _on_back(self):
        """Обработка нажатия кнопки назад"""
        if hasattr(self, '_on_back_callback'):
            self._on_back_callback()
    
    def _on_process(self):
        """Обработка нажатия кнопки обработать"""
        if hasattr(self, '_on_process_callback'):
            self._on_process_callback()
    
    def set_callbacks(self, on_back=None, on_process=None):
        """Установка callback функций"""
        if on_back:
            self._on_back_callback = on_back
        if on_process:
            self._on_process_callback = on_process
