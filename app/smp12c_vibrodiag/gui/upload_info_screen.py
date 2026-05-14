"""Экран информации о загрузке файлов"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import Dict, List, Optional
from pathlib import Path


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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loaded_sensors: Dict[int, dict] = {}  # sensor_id -> result
        self._sensor_files: Dict[int, Dict[str, str]] = {}  # sensor_id -> {file_type: filepath}
        self._turbine_name: str = "Неизвестная ВЭУ"
        self._generator_speed: str = ""
        self._active_power: str = ""
        self._record_length: str = ""
        self._record_number: str = ""
        self._record_datetime: str = ""
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        title_label = QLabel("[=] ИНФОРМАЦИЯ О ЗАГРУЗКЕ [=]")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #ff69b4;
            padding: 15px;
            border-bottom: 2px solid #333333;
        """)
        layout.addWidget(title_label)
        
        # Информация о ВЭУ и параметрах записи
        self.turbine_label = QLabel("ВЭУ: Неизвестная")
        self.turbine_label.setStyleSheet("""
            font-size: 16px;
            color: #e0e0e0;
            padding: 10px;
            background-color: #1a1a1a;
            border-radius: 5px;
        """)
        layout.addWidget(self.turbine_label)
        
        # Параметры записи
        self.params_label = QLabel("")
        self.params_label.setStyleSheet("""
            font-size: 13px;
            color: #ffa500;
            padding: 10px;
            background-color: #0a0a0a;
            border: 1px solid #333333;
            border-radius: 5px;
        """)
        self.params_label.setWordWrap(True)
        layout.addWidget(self.params_label)
        
        # Счётчик датчиков
        self.counter_label = QLabel("")
        self.counter_label.setStyleSheet("""
            font-size: 14px;
            color: #ffa500;
            padding: 10px;
            font-weight: bold;
        """)
        layout.addWidget(self.counter_label)
        
        # Список датчиков
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #333333;
                background-color: #0a0a0a;
                border-radius: 5px;
            }
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
        self.btn_back.clicked.connect(self._on_back)
        btn_layout.addWidget(self.btn_back)
        
        self.btn_process = QPushButton("[>] Обработать")
        self.btn_process.setFixedWidth(180)
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self._on_process)
        btn_layout.addWidget(self.btn_process)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
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
