"""
Р“Р»Р°РІРЅРѕРµ РѕРєРЅРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ KWF Prometheus v1.4.3

РўС‘РјРЅР°СЏ С‚РµРјР°, PySide6, Р°РЅР°Р»РёР· РґР°РЅРЅС‹С… Р’Р­РЈ.
"""

from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMenuBar, QMenu,
    QFrame, QMessageBox, QProgressBar, QStatusBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QPixmap
import qtawesome as qta  # type: ignore[import-untyped]

from .analysis_data_screen import AnalysisDataScreen
from .home_screen import HomeScreen
from .upload_info_screen import UploadInfoScreen, SENSOR_DESCRIPTIONS
from .raw_data_screen import RawDataScreen
from .migration_dialog import MigrationDialog
from .trends_screen import TrendsScreen
from .settings_dialog import SettingsDialog
from .styled_message_box import show_about, show_question, show_info, show_warning, show_critical
# from .styles import STYLESHEET  # РЈР±СЂР°Р» РґР»СЏ С‡С‘СЂРЅРѕ-Р±РµР»РѕР№ С‚РµРјС‹
from ..parsers.rd2_parser import MultiSensorRD2Parser
from ..dal.repositories import get_repository
from ..dal.repository_switcher import RepositorySwitcher
from ..dal.config import settings
from ..dal.logger import get_logger
from ..dal.persistence_service import DataPersistenceService
from ..dal.auto_scan_service import AutoScanService, ScanResult
from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_ACCENT, COLOR_BORDER, BUTTON_STYLE,
    STATUSBAR_STYLE, PROGRESSBAR_STYLE, STATUSBAR_ICON_STYLE
)

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Р“Р»Р°РІРЅРѕРµ РѕРєРЅРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"KWF Prometheus v{settings.app_version}")
        self.setMinimumSize(1400, 900)
        self.resize(1700, 1050)

        self.current_file = None
        self.parser = None

        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РїРµСЂРµРєР»СЋС‡Р°С‚РµР»СЏ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ (РґРёРЅР°РјРёС‡РµСЃРєРѕРµ РїРµСЂРµРєР»СЋС‡РµРЅРёРµ)
        self.repository_switcher = RepositorySwitcher(settings)
        self.repository_switcher.connection_success.connect(self._on_connection_success)
        self.repository_switcher.connection_failed.connect(self._on_connection_failed)
        self.repository_switcher.mode_changed.connect(self._on_mode_changed)
        
        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ С‡РµСЂРµР· РїРµСЂРµРєР»СЋС‡Р°С‚РµР»СЊ
        self.repository = self.repository_switcher.initialize()

        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ СЃРµСЂРІРёСЃР° СЃРѕС…СЂР°РЅРµРЅРёСЏ РґР°РЅРЅС‹С… (С‚РѕР»СЊРєРѕ РґР»СЏ Р‘Р”-СЂРµР¶РёРјР°)
        self.persistence_service = None
        self.auto_scan_service = None
        
        self._init_db_services()

        self.setup_ui()
        self.setup_menu()
        self.apply_styles()

    def _init_db_services(self):
        """РРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°С‚СЊ СЃРµСЂРІРёСЃС‹ Р‘Р” (РµСЃР»Рё СЂРµР¶РёРј PostgreSQL)."""
        if self.repository_switcher.mode == 'postgres':
            try:
                from ..dal.repositories.postgres import PostgresRepository
                if isinstance(self.repository, PostgresRepository):
                    self.persistence_service = DataPersistenceService(self.repository)
                    self.auto_scan_service = AutoScanService(
                        root_path=settings.archive_storage_path,
                        persistence_service=self.persistence_service,
                        interval_minutes=settings.auto_scan_interval_minutes,
                        enabled=settings.auto_scan_enabled
                    )
                    logger.info("DataPersistenceService Рё AutoScanService РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°РЅС‹")
            except Exception as e:
                logger.error("РћС€РёР±РєР° РёРЅРёС†РёР°Р»РёР·Р°С†РёРё СЃРµСЂРІРёСЃРѕРІ СЃРѕС…СЂР°РЅРµРЅРёСЏ: %s", e)
        else:
            # Р¤Р°Р№Р»РѕРІС‹Р№ СЂРµР¶РёРј вЂ” РїРѕРєР°Р·С‹РІР°РµРј РїСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ РµСЃР»Рё Р‘Р” Р±С‹Р»Р° Р·Р°РїСЂРѕС€РµРЅР°
            if settings.use_database:
                show_warning(
                    self,
                    "Р РµР¶РёРј С„Р°Р№Р»РѕРІРѕР№ СЃРёСЃС‚РµРјС‹",
                    "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕРµРґРёРЅРёС‚СЊСЃСЏ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…. "
                    "РџСЂРёР»РѕР¶РµРЅРёРµ СЂР°Р±РѕС‚Р°РµС‚ РІ С„Р°Р№Р»РѕРІРѕРј СЂРµР¶РёРјРµ. "
                    "РџСЂРѕРІРµСЂСЊС‚Рµ РїР°СЂР°РјРµС‚СЂС‹ РїРѕРґРєР»СЋС‡РµРЅРёСЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…."
                )

    def setup_ui(self):
        """РќР°СЃС‚СЂРѕРёС‚СЊ РёРЅС‚РµСЂС„РµР№СЃ."""
        # Р§С‘СЂРЅС‹Р№ С„РѕРЅ РіР»Р°РІРЅРѕРіРѕ РѕРєРЅР°
        self.setStyleSheet("QMainWindow { background-color: #000000; }")
        
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #000000;")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget {
                background-color: #000000;
            }
            QTabWidget::pane {
                border: none;
                background-color: #000000;
                margin: 0px;
                padding: 0px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #1A1A1A;
                color: #888888;
                padding: 8px 20px;
                border: none;
                font-size: 12px;
                margin-bottom: 0px;
            }
            QTabBar::tab:selected {
                background-color: #000000;
                color: #FFFFFF;
                border-bottom: 2px solid #FFFFFF;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2A2A2A;
                color: #CCCCCC;
            }
        """)
        main_layout.addWidget(self.tabs)

        # РЎС‚Р°С‚СѓСЃ-Р±Р°СЂ СЃ РёРЅРґРёРєР°С‚РѕСЂРѕРј РїСЂРѕРіСЂРµСЃСЃР°
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet(STATUSBAR_STYLE)
        self.setStatusBar(self.status_bar)
        
        # РРєРѕРЅРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ (СЃР»РµРІР°) вЂ” С‚РѕР»СЊРєРѕ РёРєРѕРЅРєР° РёР· QtAwesome
        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet(STATUSBAR_ICON_STYLE)
        self.status_bar.addPermanentWidget(self.status_icon, stretch=0)
        
        # РРЅРґРёРєР°С‚РѕСЂ РїСЂРѕРіСЂРµСЃСЃР° (СЃРїСЂР°РІР°) вЂ” СЃРєСЂС‹С‚ РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(PROGRESSBAR_STYLE)
        self.status_bar.addPermanentWidget(self.progress_bar, stretch=0)

        # РњРµС‚РєР° РІСЂРµРјРµРЅРё (СЃРїСЂР°РІР°)
        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px; padding: 0px 8px;")
        self.status_bar.addPermanentWidget(self.time_label, stretch=0)
        
        # РРЅРґРёРєР°С‚РѕСЂ СЂРµР¶РёРјР° (PostgreSQL / Р¤Р°Р№Р»РѕРІС‹Р№)
        self.mode_indicator = QLabel()
        self.mode_indicator.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px; padding: 0px 8px;")
        self.status_bar.addPermanentWidget(self.mode_indicator, stretch=0)
        
        # РўР°Р№РјРµСЂ РґР»СЏ РѕР±РЅРѕРІР»РµРЅРёСЏ РІСЂРµРјРµРЅРё
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

        # Р’РєР»Р°РґРєР° Home (РїРµСЂРµРґР°С‘Рј СЂРµРїРѕР·РёС‚РѕСЂРёР№ Рё СЃРµСЂРІРёСЃС‹)
        self.home_screen = HomeScreen(
            repository=self.repository,
            persistence_service=self.persistence_service,
            auto_scan_service=self.auto_scan_service
        )
        self.home_screen.analyze_requested.connect(self._on_upload_info_requested)
        self.tabs.addTab(self.home_screen, "Home")

        # Р’РєР»Р°РґРєР° РРЅС„РѕСЂРјР°С†РёСЏ Рѕ Р·Р°РіСЂСѓР·РєРµ
        self.upload_info_screen = UploadInfoScreen(repository=self.repository)
        self.upload_info_screen.set_callbacks(
            on_back=self._on_upload_info_back,
            on_process=self._on_upload_info_process
        )
        self.tabs.addTab(self.upload_info_screen, "РРЅС„РѕСЂРјР°С†РёСЏ")

        # Р’РєР»Р°РґРєР° РЎС‹СЂС‹Рµ РґР°РЅРЅС‹Рµ
        self.raw_data_screen = RawDataScreen()
        self.raw_data_screen.set_back_callback(self._on_raw_data_back)
        self.raw_data_screen.set_analyze_callback(self._on_raw_data_analyze)
        self.tabs.addTab(self.raw_data_screen, "РЎС‹СЂС‹Рµ РґР°РЅРЅС‹Рµ")

        # Р’РєР»Р°РґРєР° РђРЅР°Р»РёР· РґР°РЅРЅС‹С…
        self.analysis_screen = AnalysisDataScreen()
        self.tabs.addTab(self.analysis_screen, "РђРЅР°Р»РёР· РґР°РЅРЅС‹С…")

        # Р’РєР»Р°РґРєР° РўСЂРµРЅРґС‹
        self.trends_screen = TrendsScreen(repository=self.repository)
        self.tabs.addTab(self.trends_screen, "РўСЂРµРЅРґС‹")

        # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РёРєРѕРЅРєРё СЃС‚Р°С‚СѓСЃР°
        self._update_status_icon('db' if self.repository_switcher.mode == 'postgres' else 'file')
        self._update_mode_indicator()

    def _on_upload_info_requested(self, parser):
        """РџРµСЂРµР№С‚Рё РЅР° СЌРєСЂР°РЅ РёРЅС„РѕСЂРјР°С†РёРё Рѕ Р·Р°РіСЂСѓР·РєРµ."""
        self.parser = parser
        self.current_file = self.home_screen.current_file
        
        # РџРѕР»СѓС‡Р°РµРј РјРµС‚СЂРёРєРё С‚СѓСЂР±РёРЅС‹
        metrics = parser.get_turbine_metrics()
        
        # РЎРѕР±РёСЂР°РµРј РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ Р·Р°РіСЂСѓР¶РµРЅРЅС‹С… РґР°С‚С‡РёРєР°С… Рё С„Р°Р№Р»Р°С…
        loaded_sensors = {}
        sensor_files = {}
        
        for sensor_id in range(1, 9):
            data = parser.get_sensor_data(sensor_id)
            if data:
                loaded_sensors[sensor_id] = data
                sensor_files[sensor_id] = {}
                
                if data.get('acceleration') is not None:
                    sensor_files[sensor_id]['FILTER'] = True
                if data.get('velocity') is not None:
                    sensor_files[sensor_id]['LOW'] = True
                if data.get('high_freq') is not None:
                    sensor_files[sensor_id]['HIGH'] = True
        
        # Р¤РѕСЂРјРёСЂСѓРµРј РґР°РЅРЅС‹Рµ РґР»СЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ
        turbine_name = self._extract_wtg_from_path(self.current_file) if self.current_file else "РќРµРёР·РІРµСЃС‚РЅР°СЏ"
        generator_speed = f"{metrics.get('generator_speed_rpm', 0):.0f} RPM" if metrics.get('generator_speed_rpm') else ""
        active_power = f"{metrics.get('power_kw', 0):.0f} KW" if metrics.get('power_kw') else ""
        
        # РџРѕР»СѓС‡Р°РµРј record_number Рё record_datetime РёР· РјРµС‚Р°РґР°РЅРЅС‹С… РїР°СЂСЃРµСЂР°
        record_number = ""
        record_datetime = ""
        if hasattr(parser, 'turbine_metadata') and parser.turbine_metadata:
            record_number = str(parser.turbine_metadata.get('record_number', ''))[:5]
            record_datetime = parser.turbine_metadata.get('record_datetime', '')
        
        # РџРѕР»СѓС‡Р°РµРј РґР»РёРЅСѓ Р·Р°РїРёСЃРё РёР· РјРµС‚Р°РґР°РЅРЅС‹С…
        record_length = ""
        if hasattr(parser, 'turbine_metadata') and parser.turbine_metadata:
            rl = parser.turbine_metadata.get('record_length', 0)
            if rl:
                record_length = f"{rl:.0f} s"
        
        self.upload_info_screen.set_upload_data(
            turbine_name=turbine_name,
            loaded_sensors=loaded_sensors,
            sensor_files=sensor_files,
            generator_speed=generator_speed,
            active_power=active_power,
            record_length=record_length,
            record_number=record_number,
            record_datetime=record_datetime
        )

        # === РЎР РђР—РЈ Р·Р°РіСЂСѓР¶Р°РµРј РґР°РЅРЅС‹Рµ РІ RawDataScreen Рё AnalysisDataScreen ===
        self._prepare_raw_data()
        self.analysis_screen.set_parser(self.parser)

        self.tabs.setCurrentWidget(self.upload_info_screen)
        self.status_icon.setToolTip(
            f"Р—Р°РіСЂСѓР¶РµРЅРѕ: {Path(self.current_file).name if self.current_file else 'С„Р°Р№Р»'}"
        )

    def _prepare_raw_data(self):
        """РџРѕРґРіРѕС‚РѕРІРёС‚СЊ РґР°РЅРЅС‹Рµ РґР»СЏ СЌРєСЂР°РЅР° СЃС‹СЂС‹С… РґР°РЅРЅС‹С…."""
        if not self.parser:
            return
        
        raw_sensor_data = {}
        for sensor_id in range(1, 9):
            data = self.parser.get_sensor_data(sensor_id)
            if data:
                signal_data = None
                time_data = None
                
                if data.get('acceleration') is not None and len(data['acceleration']) > 0:
                    signal_data = np.asarray(data['acceleration'])
                    time_data = np.asarray(data['acceleration_time'])
                elif data.get('velocity') is not None and len(data['velocity']) > 0:
                    signal_data = np.asarray(data['velocity'])
                    time_data = np.asarray(data['velocity_time'])
                elif data.get('high_freq') is not None and len(data['high_freq']) > 0:
                    signal_data = np.asarray(data['high_freq'])
                    time_data = np.asarray(data['high_freq_time'])

                if signal_data is not None and time_data is not None and len(signal_data) > 0:
                    raw_sensor_data[sensor_id] = {
                        'time': time_data,
                        'signal': signal_data,
                        'name': SENSOR_DESCRIPTIONS.get(sensor_id, f"Р”Р°С‚С‡РёРє {sensor_id}")
                    }
        
        self.raw_data_screen.set_sensor_data(raw_sensor_data)

    def _on_upload_info_back(self):
        """Р’РµСЂРЅСѓС‚СЊСЃСЏ РЅР° Home РёР· СЌРєСЂР°РЅР° РёРЅС„РѕСЂРјР°С†РёРё."""
        self.tabs.setCurrentWidget(self.home_screen)

    def _on_upload_info_process(self):
        """РџРµСЂРµР№С‚Рё Рє СЌРєСЂР°РЅСѓ СЃС‹СЂС‹С… РґР°РЅРЅС‹С…."""
        if not self.parser:
            return
        
        # РЎРѕР±РёСЂР°РµРј РґР°РЅРЅС‹Рµ РґР»СЏ raw_data_screen
        raw_sensor_data = {}
        available_sensors = self.parser.get_available_sensors()
        
        # РћС‚Р»Р°РґРѕС‡РЅС‹Р№ Р»РѕРі
        import tempfile, datetime
        log_path = Path(tempfile.gettempdir()) / "vibrodiag_debug.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== Debug log {datetime.datetime.now()} ===\n")
            f.write(f"Available sensors: {available_sensors}\n")
            
            for sensor_id in range(1, 9):
                data = self.parser.get_sensor_data(sensor_id)
                if data:
                    f.write(f"Sensor {sensor_id} data keys: {list(data.keys())}\n")
                    
                    # Р‘РµСЂС‘Рј РїРµСЂРІС‹Р№ РґРѕСЃС‚СѓРїРЅС‹Р№ СЃРёРіРЅР°Р» РґР»СЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ
                    signal_data = None
                    time_data = None
                    
                    if data.get('acceleration') is not None and len(data['acceleration']) > 0:
                        signal_data = np.asarray(data['acceleration'])
                        time_data = np.asarray(data['acceleration_time'])
                        f.write(f"  Sensor {sensor_id}: using acceleration, len={len(signal_data)}\n")
                    elif data.get('velocity') is not None and len(data['velocity']) > 0:
                        signal_data = np.asarray(data['velocity'])
                        time_data = np.asarray(data['velocity_time'])
                        f.write(f"  Sensor {sensor_id}: using velocity, len={len(signal_data)}\n")
                    elif data.get('high_freq') is not None and len(data['high_freq']) > 0:
                        signal_data = np.asarray(data['high_freq'])
                        time_data = np.asarray(data['high_freq_time'])
                        f.write(f"  Sensor {sensor_id}: using high_freq, len={len(signal_data)}\n")
                    else:
                        f.write(f"  Sensor {sensor_id}: no signal data found\n")

                    if signal_data is not None and time_data is not None and len(signal_data) > 0:
                        raw_sensor_data[sensor_id] = {
                            'time': time_data,
                            'signal': signal_data,
                            'name': SENSOR_DESCRIPTIONS.get(sensor_id, f"Р”Р°С‚С‡РёРє {sensor_id}")
                        }
                else:
                    f.write(f"Sensor {sensor_id}: no data\n")
            
            f.write(f"Total sensors with data: {list(raw_sensor_data.keys())}\n")
        
        self.raw_data_screen.set_sensor_data(raw_sensor_data)
        self.tabs.setCurrentWidget(self.raw_data_screen)
        self.status_icon.setToolTip("РџСЂРѕСЃРјРѕС‚СЂ СЃС‹СЂС‹С… РґР°РЅРЅС‹С…")

    def _on_raw_data_back(self):
        """Р’РµСЂРЅСѓС‚СЊСЃСЏ РЅР° СЌРєСЂР°РЅ РёРЅС„РѕСЂРјР°С†РёРё РёР· СЃС‹СЂС‹С… РґР°РЅРЅС‹С…."""
        self.tabs.setCurrentWidget(self.upload_info_screen)

    def _on_raw_data_analyze(self):
        """РџРµСЂРµР№С‚Рё Рє Р°РЅР°Р»РёР·Сѓ РґР°РЅРЅС‹С… РёР· СЌРєСЂР°РЅР° СЃС‹СЂС‹С… РґР°РЅРЅС‹С…."""
        if self.parser is None:
            return
        self.analysis_screen.set_parser(self.parser)
        self.tabs.setCurrentWidget(self.analysis_screen)
        available = self.parser.get_available_sensors()
        self.status_icon.setToolTip(
            f"РђРЅР°Р»РёР·: {Path(self.current_file).name if self.current_file else 'С„Р°Р№Р»'} | Р”Р°С‚С‡РёРєРё: {available}"
        )

    def setup_menu(self):
        """РќР°СЃС‚СЂРѕРёС‚СЊ РјРµРЅСЋ."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #000000;
                color: #FFFFFF;
                border: none;
            }
            QMenuBar::item {
                background-color: #000000;
                color: #FFFFFF;
                padding: 4px 12px;
            }
            QMenuBar::item:selected {
                background-color: #333333;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #333333;
            }
            QMenu::item:selected {
                background-color: #333333;
                color: #FFFFFF;
            }
        """)

        # РњРµРЅСЋ Р¤Р°Р№Р»
        file_menu = menubar.addMenu("Р¤Р°Р№Р»")

        open_action = QAction("РћС‚РєСЂС‹С‚СЊ Р°СЂС…РёРІ...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_archive)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # РњРµРЅСЋ Р­РєСЃРїРѕСЂС‚
        export_menu = file_menu.addMenu("Р­РєСЃРїРѕСЂС‚")

        export_csv_action = QAction("CSV...", self)
        export_csv_action.triggered.connect(self._export_csv_from_menu)
        export_menu.addAction(export_csv_action)

        export_excel_action = QAction("Excel...", self)
        export_excel_action.triggered.connect(self._export_excel_from_menu)
        export_menu.addAction(export_excel_action)

        export_pdf_action = QAction("PDF-РѕС‚С‡С‘С‚...", self)
        export_pdf_action.triggered.connect(self._export_pdf_from_menu)
        export_menu.addAction(export_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("Р’С‹С…РѕРґ", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # РњРµРЅСЋ РђРЅР°Р»РёР·
        analysis_menu = menubar.addMenu("РђРЅР°Р»РёР·")

        trends_action = QAction("Р“СЂР°С„РёРє С‚СЂРµРЅРґРѕРІ", self)
        trends_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.trends_screen))
        analysis_menu.addAction(trends_action)

        # РњРµРЅСЋ РќР°СЃС‚СЂРѕР№РєРё
        settings_menu = menubar.addMenu("РќР°СЃС‚СЂРѕР№РєРё")

        settings_action = QAction("РќР°СЃС‚СЂРѕР№РєРё РїСЂРёР»РѕР¶РµРЅРёСЏ...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

        # РњРµРЅСЋ РЎРїСЂР°РІРєР°
        help_menu = menubar.addMenu("РЎРїСЂР°РІРєР°")

        about_action = QAction("Рћ РїСЂРѕРіСЂР°РјРјРµ", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        """РџРѕРєР°Р·Р°С‚СЊ РґРёР°Р»РѕРі В«Рћ РїСЂРѕРіСЂР°РјРјРµВ»."""
        mode_text = "PostgreSQL" if settings.use_database else "Р¤Р°Р№Р»РѕРІР°СЏ СЃРёСЃС‚РµРјР°"
        show_about(
            self,
            "Рћ РїСЂРѕРіСЂР°РјРјРµ",
            f"<h2>KWF Prometheus</h2>"
            f"<p><b>Р’РµСЂСЃРёСЏ:</b> {settings.app_version}</p>"
            f"<p><b>Р РµР¶РёРј С…СЂР°РЅРµРЅРёСЏ:</b> {mode_text}</p>"
            f"<p>РЎРёСЃС‚РµРјР° Р°РЅР°Р»РёР·Р° Рё РІРёР±СЂР°С†РёРѕРЅРЅРѕР№ РґРёР°РіРЅРѕСЃС‚РёРєРё Р’Р­РЈ</p>"
            f"<p><b>РЎС‚Р°РЅРґР°СЂС‚С‹:</b> ISO 10816-21:2015, Р“РћРЎРў 10816-21-2021</p>"
            f"<p><b></b> A.Telezhenko, 2026</p>"
        )

    def _on_connection_success(self, info: str):
        """РћР±СЂР°Р±РѕС‚РєР° СѓСЃРїРµС€РЅРѕРіРѕ РїРѕРґРєР»СЋС‡РµРЅРёСЏ."""
        logger.info(info)
        if hasattr(self, 'mode_indicator'):
            self._update_mode_indicator()

    def _on_connection_failed(self, error: str):
        """РћР±СЂР°Р±РѕС‚РєР° РѕС€РёР±РєРё РїРѕРґРєР»СЋС‡РµРЅРёСЏ."""
        logger.error(error)
        if hasattr(self, 'mode_indicator'):
            show_warning(self, "РћС€РёР±РєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ", error)
            self._update_mode_indicator()

    def _on_mode_changed(self, mode: str):
        """РћР±СЂР°Р±РѕС‚С‡РёРє РёР·РјРµРЅРµРЅРёСЏ СЂРµР¶РёРјР° (file/postgres)."""
        logger.info(f"Р РµР¶РёРј РёР·РјРµРЅС‘РЅ: {mode}")
        
        if not hasattr(self, 'status_icon'):
            return
        self._update_status_icon('db' if mode == 'postgres' else 'file')
        self._update_mode_indicator()
        
        # РџРµСЂРµСЃРѕР·РґР°С‘Рј СЃРµСЂРІРёСЃС‹
        self.persistence_service = None
        self.auto_scan_service = None
        if mode == 'postgres':
            self._init_db_services()
        
        # РћР±РЅРѕРІР»СЏРµРј РІСЃРµ СЌРєСЂР°РЅС‹ СЃ РЅРѕРІС‹Рј СЂРµРїРѕР·РёС‚РѕСЂРёРµРј
        self._update_all_screens()

    def _update_all_screens(self):
        """РћР±РЅРѕРІРёС‚СЊ СЂРµРїРѕР·РёС‚РѕСЂРёРё РІРѕ РІСЃРµС… СЌРєСЂР°РЅР°С…."""
        logger.info("РћР±РЅРѕРІР»РµРЅРёРµ СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ РІРѕ РІСЃРµС… СЌРєСЂР°РЅР°С…...")
        
        # РћР±РЅРѕРІР»СЏРµРј HomeScreen
        if hasattr(self, 'home_screen'):
            self.home_screen.set_repository(self.repository_switcher.repository)
            self.home_screen.persistence_service = self.persistence_service
            self.home_screen.auto_scan_service = self.auto_scan_service
        
        # РћР±РЅРѕРІР»СЏРµРј TrendsScreen
        if hasattr(self, 'trends_screen'):
            self.trends_screen.repository = self.repository_switcher.repository
        
        # РћР±РЅРѕРІР»СЏРµРј UploadInfoScreen
        if hasattr(self, 'upload_info_screen'):
            self.upload_info_screen.repository = self.repository_switcher.repository
        
        logger.info("Р’СЃРµ СЌРєСЂР°РЅС‹ РѕР±РЅРѕРІР»РµРЅС‹")

    def _update_mode_indicator(self):
        """РћР±РЅРѕРІРёС‚СЊ РёРЅРґРёРєР°С‚РѕСЂ СЂРµР¶РёРјР° РІ СЃС‚Р°С‚СѓСЃ-Р±Р°СЂРµ."""
        if not hasattr(self, 'repository_switcher') or not self.repository_switcher:
            return
        
        # РџРѕР»СѓС‡Р°РµРј СЂРµР¶РёРј РЅР°РїСЂСЏРјСѓСЋ РёР· switcher
        mode = self.repository_switcher.mode
        info = self.repository_switcher.get_repository_info()
        
        if mode == 'postgres':
            host = info.get('host', settings.db_host)
            port = info.get('port', settings.db_port)
            text = f"Р РµР¶РёРј: PostgreSQL ({host}:{port})"
            color = "#448AFF"  # РЎРёРЅРёР№
        else:
            text = "Р РµР¶РёРј: Р¤Р°Р№Р»РѕРІР°СЏ СЃРёСЃС‚РµРјР°"
            color = "#888888"  # РЎРµСЂС‹Р№
        
        if hasattr(self, 'mode_indicator'):
            self.mode_indicator.setText(text)
            self.mode_indicator.setStyleSheet(
                f"color: {color}; font-size: 10px; padding: 0px 8px;"
            )

    def _open_settings(self):
        """РћС‚РєСЂС‹С‚СЊ РґРёР°Р»РѕРі РЅР°СЃС‚СЂРѕРµРє."""
        dialog = SettingsDialog(self, repository_switcher=self.repository_switcher)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.archives_found.connect(self.home_screen.add_archives)
        dialog.switch_to_home.connect(lambda: self.tabs.setCurrentIndex(0))
        dialog.exec()

    def _on_settings_changed(self):
        """РћР±СЂР°Р±РѕС‚С‡РёРє РёР·РјРµРЅРµРЅРёСЏ РЅР°СЃС‚СЂРѕРµРє (РґРёРЅР°РјРёС‡РµСЃРєРѕРµ РїСЂРёРјРµРЅРµРЅРёРµ)."""
        logger.info("РџСЂРёРјРµРЅРµРЅРёРµ РёР·РјРµРЅРµРЅРёР№ РЅР°СЃС‚СЂРѕРµРє...")
        
        # РџРµСЂРµРєР»СЋС‡Р°РµРј СЂРµРїРѕР·РёС‚РѕСЂРёР№ С‡РµСЂРµР· RepositorySwitcher
        try:
            self.repository = self.repository_switcher.switch_mode(settings.use_database)
            logger.info(f"Р РµРїРѕР·РёС‚РѕСЂРёР№ РїРµСЂРµРєР»СЋС‡С‘РЅ: {self.repository_switcher.mode}")
            
            # РЎРќРђР§РђР›Рђ РѕР±РЅРѕРІР»СЏРµРј РІСЃРµ СЌРєСЂР°РЅС‹ СЃ РЅРѕРІС‹Рј СЂРµРїРѕР·РёС‚РѕСЂРёРµРј
            self._update_all_screens()
            
            # РџРµСЂРµСЃРѕР·РґР°С‘Рј persistence_service РµСЃР»Рё РЅСѓР¶РЅРѕ
            if settings.use_database and self.repository_switcher.mode == 'postgres':
                try:
                    from ..dal.repositories.postgres import PostgresRepository
                    from ..dal.persistence_service import DataPersistenceService
                    
                    if isinstance(self.repository, PostgresRepository):
                        self.persistence_service = DataPersistenceService(self.repository)
                        logger.info("DataPersistenceService РѕР±РЅРѕРІР»С‘РЅ РґР»СЏ PostgreSQL")
                except Exception as e:
                    logger.error(f"РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ DataPersistenceService: {e}")
            else:
                self.persistence_service = None
            
            # РџРћРўРћРњ РѕР±РЅРѕРІР»СЏРµРј РёРЅРґРёРєР°С‚РѕСЂ СЂРµР¶РёРјР° (РїРѕСЃР»Рµ РїРµСЂРµРєР»СЋС‡РµРЅРёСЏ)
            self._update_mode_indicator()
            self._update_status_icon('db' if self.repository_switcher.mode == 'postgres' else 'file')
            
            show_info(
                self,
                "РќР°СЃС‚СЂРѕР№РєРё РїСЂРёРјРµРЅРµРЅС‹",
                f"Р РµР¶РёРј РёР·РјРµРЅС‘РЅ РЅР°: {'PostgreSQL' if self.repository_switcher.mode == 'postgres' else 'Р¤Р°Р№Р»РѕРІР°СЏ СЃРёСЃС‚РµРјР°'}"
            )
        except Exception as e:
            logger.error(f"РћС€РёР±РєР° РїСЂРё РїРµСЂРµРєР»СЋС‡РµРЅРёРё СЂРµРїРѕР·РёС‚РѕСЂРёСЏ: {e}", exc_info=True)
            show_warning(
                self,
                "РћС€РёР±РєР° РїРµСЂРµРєР»СЋС‡РµРЅРёСЏ",
                f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРµСЂРµРєР»СЋС‡РёС‚СЊ СЂРµР¶РёРј: {e}\nРџСЂРёР»РѕР¶РµРЅРёРµ РїСЂРѕРґРѕР»Р¶РёС‚ СЂР°Р±РѕС‚Сѓ РІ РїСЂРµРґС‹РґСѓС‰РµРј СЂРµР¶РёРјРµ."
            )

    def _update_time(self):
        """РћР±РЅРѕРІРёС‚СЊ РІСЂРµРјСЏ РІ СЃС‚Р°С‚СѓСЃ-Р±Р°СЂРµ."""
        from datetime import datetime
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _update_status_icon(self, state: str):
        """РћР±РЅРѕРІРёС‚СЊ РёРєРѕРЅРєСѓ СЃС‚Р°С‚СѓСЃ-Р±Р°СЂР°."""
        icons = {
            'ready': ('mdi.check-circle', '#00C853'),      # Р—РµР»С‘РЅР°СЏ вЂ” РіРѕС‚РѕРІРѕ
            'loading': ('mdi.loading', '#FFC107'),          # Р–С‘Р»С‚Р°СЏ вЂ” Р·Р°РіСЂСѓР·РєР°
            'error': ('mdi.alert-circle', '#DD2C00'),       # РљСЂР°СЃРЅР°СЏ вЂ” РѕС€РёР±РєР°
            'db': ('mdi.database', '#448AFF'),              # РЎРёРЅСЏСЏ вЂ” Р‘Р”
            'file': ('mdi.folder', '#888888'),              # РЎРµСЂР°СЏ вЂ” С„Р°Р№Р»С‹
        }
        icon_name, color = icons.get(state, icons['ready'])
        pixmap = qta.icon(icon_name, color=color).pixmap(16, 16)
        self.status_icon.setPixmap(pixmap)
        self.status_icon.setToolTip(
            "Р“РѕС‚РѕРІРѕ Рє СЂР°Р±РѕС‚Рµ" if state == 'ready' else
            "Р—Р°РіСЂСѓР·РєР°..." if state == 'loading' else
            "РћС€РёР±РєР°" if state == 'error' else
            "Р РµР¶РёРј: PostgreSQL" if state == 'db' else
            "Р РµР¶РёРј: Р¤Р°Р№Р»РѕРІР°СЏ СЃРёСЃС‚РµРјР°" if state == 'file' else ""
        )

    def show_status_message(self, message: str, icon_name: str = "mdi.info", duration_ms: int = 5000):
        """
        РџРѕРєР°Р·Р°С‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ РІ СЃС‚Р°С‚СѓСЃ-Р±Р°СЂРµ СЃ РёРєРѕРЅРєРѕР№.
        
        Args:
            message: РўРµРєСЃС‚ СЃРѕРѕР±С‰РµРЅРёСЏ
            icon_name: РРєРѕРЅРєР° QtAwesome (РЅР°РїСЂРёРјРµСЂ, "mdi.info", "mdi.check-circle")
            duration_ms: Р’СЂРµРјСЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ РІ РјРёР»Р»РёСЃРµРєСѓРЅРґР°С… (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 5000)
        """
        self.status_bar.showMessage(message, duration_ms)
        
        # Р’СЂРµРјРµРЅРЅРѕ РјРµРЅСЏРµРј РёРєРѕРЅРєСѓ
        old_icon = self.status_icon.toolTip()
        pixmap = qta.icon(icon_name, color='#448AFF').pixmap(16, 16)
        self.status_icon.setPixmap(pixmap)
        self.status_icon.setToolTip(message)
        
        # Р’РѕР·РІСЂР°С‰Р°РµРј РёРєРѕРЅРєСѓ С‡РµСЂРµР· С‚Р°Р№РјРµСЂ
        QTimer.singleShot(duration_ms, lambda: self._update_status_icon(
            'db' if settings.use_database else 'file'
        ))

    def show_progress(self, message: str = "Р—Р°РіСЂСѓР·РєР°..."):
        """РџРѕРєР°Р·Р°С‚СЊ РёРЅРґРёРєР°С‚РѕСЂ РїСЂРѕРіСЂРµСЃСЃР°."""
        self.progress_bar.setRange(0, 0)  # Р‘РµСЃРєРѕРЅРµС‡РЅС‹Р№ РїСЂРѕРіСЂРµСЃСЃ
        self.progress_bar.setVisible(True)
        self._update_status_icon('loading')

    def hide_progress(self, message: str = "Р“РѕС‚РѕРІ Рє СЂР°Р±РѕС‚Рµ"):
        """РЎРєСЂС‹С‚СЊ РёРЅРґРёРєР°С‚РѕСЂ РїСЂРѕРіСЂРµСЃСЃР°."""
        self.progress_bar.setVisible(False)
        self._update_status_icon('db' if settings.use_database else 'file')

    def set_progress_value(self, value: int, max_value: int = 100):
        """РЈСЃС‚Р°РЅРѕРІРёС‚СЊ Р·РЅР°С‡РµРЅРёРµ РїСЂРѕРіСЂРµСЃСЃР° (0-100)."""
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(value)
        self.progress_bar.setVisible(True)
        self._update_status_icon('loading')

    def apply_styles(self):
        """РџСЂРёРјРµРЅРёС‚СЊ СЃС‚РёР»Рё (Р·Р°РєРѕРјРјРµРЅС‚РёСЂРѕРІР°РЅРѕ РґР»СЏ С‡С‘СЂРЅРѕ-Р±РµР»РѕР№ С‚РµРјС‹ Home)."""
        # self.setStyleSheet(STYLESHEET)

        # Р“Р»РѕР±Р°Р»СЊРЅР°СЏ С‚С‘РјРЅР°СЏ С‚РµРјР° РґР»СЏ QFileDialog
        self.setStyleSheet("""
            QFileDialog {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QFileDialog QListView,
            QFileDialog QTreeView {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QFileDialog QListView::item,
            QFileDialog QTreeView::item {
                color: #FFFFFF;
                padding: 4px;
            }
            QFileDialog QListView::item:selected,
            QFileDialog QTreeView::item:selected {
                background-color: #333333;
                color: #FFFFFF;
                border-radius: 2px;
            }
            QFileDialog QHeaderView::section {
                background-color: #2A2A2A;
                color: #FFFFFF;
                padding: 6px;
                border: 1px solid #333333;
                font-weight: bold;
            }
            QFileDialog QLineEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 4px;
            }
            QFileDialog QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QFileDialog QPushButton:hover {
                background-color: #E8E8E8;
            }
            QFileDialog QPushButton:pressed {
                background-color: #D0D0D0;
            }
            QFileDialog QLabel {
                color: #FFFFFF;
            }
            QFileDialog QComboBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 4px;
            }
            QFileDialog QComboBox::drop-down {
                border: none;
            }
            QFileDialog QComboBox QAbstractItemView {
                background-color: #2D2D2D;
                color: #FFFFFF;
                selection-background-color: #333333;
            }
            QFileDialog QFrame {
                border: 1px solid #333333;
            }
        """)

    def _extract_wtg_from_path(self, path: str) -> str:
        """РР·РІР»РµС‡СЊ WTG РёР· РїСѓС‚Рё Рє С„Р°Р№Р»Сѓ."""
        import re
        match = re.search(r'WTG(\d{1,2})', Path(path).name, re.IGNORECASE)
        if match:
            return f"WTG{int(match.group(1))}"
        return "РќРµРёР·РІРµСЃС‚РЅР°СЏ"

    def load_archive(self):
        """Р—Р°РіСЂСѓР·РёС‚СЊ Р°СЂС…РёРІ СЃ РґР°РЅРЅС‹РјРё (С‡РµСЂРµР· РјРµРЅСЋ Р¤Р°Р№Р»)."""
        self.home_screen._load_archive()

    def _export_csv_from_menu(self):
        """Р­РєСЃРїРѕСЂС‚ РІ CSV РёР· РјРµРЅСЋ."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_csv()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "РќРµС‚ РґР°РЅРЅС‹С…", "РЎРЅР°С‡Р°Р»Р° Р·Р°РіСЂСѓР·РёС‚Рµ С„Р°Р№Р» РґР»СЏ Р°РЅР°Р»РёР·Р°.")

    def _export_excel_from_menu(self):
        """Р­РєСЃРїРѕСЂС‚ РІ Excel РёР· РјРµРЅСЋ."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_excel()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "РќРµС‚ РґР°РЅРЅС‹С…", "РЎРЅР°С‡Р°Р»Р° Р·Р°РіСЂСѓР·РёС‚Рµ С„Р°Р№Р» РґР»СЏ Р°РЅР°Р»РёР·Р°.")

    def _export_pdf_from_menu(self):
        """Р­РєСЃРїРѕСЂС‚ РІ PDF РёР· РјРµРЅСЋ."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_pdf()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "РќРµС‚ РґР°РЅРЅС‹С…", "РЎРЅР°С‡Р°Р»Р° Р·Р°РіСЂСѓР·РёС‚Рµ С„Р°Р№Р» РґР»СЏ Р°РЅР°Р»РёР·Р°.")

    def closeEvent(self, event):
        """РћР±СЂР°Р±РѕС‚РєР° Р·Р°РєСЂС‹С‚РёСЏ РѕРєРЅР°."""
        reply = show_question(
            self,
            "РџРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ",
            "Р’С‹ СѓРІРµСЂРµРЅС‹, С‡С‚Рѕ С…РѕС‚РёС‚Рµ Р·Р°РєСЂС‹С‚СЊ РїСЂРёР»РѕР¶РµРЅРёРµ?"
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

