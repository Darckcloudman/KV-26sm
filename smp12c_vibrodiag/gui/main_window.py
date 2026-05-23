"""
Главное окно приложения SMP12C VibroDiag Analyzer v1.3

Тёмная тема, PySide6, анализ данных ВЭУ.
С поддержкой DAL (Data Access Layer) и PostgreSQL.
"""

from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMenuBar, QMenu,
    QFrame, QMessageBox, QProgressBar, QStatusBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
import qtawesome as qta

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QAction

from .analysis_data_screen import AnalysisDataScreen
from .home_screen import HomeScreen
from .upload_info_screen import UploadInfoScreen, SENSOR_DESCRIPTIONS
from .raw_data_screen import RawDataScreen
from .migration_dialog import MigrationDialog
from .trends_screen import TrendsScreen
from .settings_dialog import SettingsDialog
from .styled_message_box import show_about, show_question, show_info, show_warning, show_critical
# from .styles import STYLESHEET  # Убрал для чёрно-белой темы
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
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SMP12C VibroDiag Analyzer v{settings.app_version}")
        self.setMinimumSize(1400, 900)
        self.resize(1700, 1050)

        self.current_file = None
        self.parser = None

        # Инициализация переключателя репозитория (динамическое переключение)
        self.repository_switcher = RepositorySwitcher(settings)
        self.repository_switcher.connection_success.connect(self._on_connection_success)
        self.repository_switcher.connection_failed.connect(self._on_connection_failed)
        self.repository_switcher.mode_changed.connect(self._on_mode_changed)
        
        # Инициализация репозитория через переключатель
        self.repository = self.repository_switcher.initialize()

        # Инициализация сервиса сохранения данных (только для БД-режима)
        self.persistence_service = None
        self.auto_scan_service = None
        
        self._init_db_services()

        self.setup_ui()
        self.setup_menu()
        self.apply_styles()

    def _init_db_services(self):
        """Инициализировать сервисы БД (если режим PostgreSQL)."""
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
                    logger.info("DataPersistenceService и AutoScanService инициализированы")
            except Exception as e:
                logger.error("Ошибка инициализации сервисов сохранения: %s", e)
        else:
            # Файловый режим — показываем предупреждение если БД была запрошена
            if settings.use_database:
                show_warning(
                    self,
                    "Режим файловой системы",
                    "Не удалось соединиться с базой данных. "
                    "Приложение работает в файловом режиме. "
                    "Проверьте параметры подключения в настройках."
                )

    def setup_ui(self):
        """Настроить интерфейс."""
        # Чёрный фон главного окна
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

        # Вкладка Home (передаём репозиторий и сервисы)
        self.home_screen = HomeScreen(
            repository=self.repository,
            persistence_service=self.persistence_service,
            auto_scan_service=self.auto_scan_service
        )
        self.home_screen.analyze_requested.connect(self._on_upload_info_requested)
        self.tabs.addTab(self.home_screen, "Home")

        # Вкладка Информация о загрузке
        self.upload_info_screen = UploadInfoScreen(repository=self.repository)
        self.upload_info_screen.set_callbacks(
            on_back=self._on_upload_info_back,
            on_process=self._on_upload_info_process
        )
        self.tabs.addTab(self.upload_info_screen, "Информация")

        # Вкладка Сырые данные
        self.raw_data_screen = RawDataScreen()
        self.raw_data_screen.set_back_callback(self._on_raw_data_back)
        self.raw_data_screen.set_analyze_callback(self._on_raw_data_analyze)
        self.tabs.addTab(self.raw_data_screen, "Сырые данные")

        # Вкладка Анализ данных
        self.analysis_screen = AnalysisDataScreen()
        self.tabs.addTab(self.analysis_screen, "Анализ данных")

        # Вкладка Тренды
        self.trends_screen = TrendsScreen(repository=self.repository)
        self.tabs.addTab(self.trends_screen, "Тренды")

        # Статус-бар с индикатором прогресса
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet(STATUSBAR_STYLE)
        self.setStatusBar(self.status_bar)
        
        # Иконка состояния (слева) — только иконка из QtAwesome
        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_icon.setStyleSheet(STATUSBAR_ICON_STYLE)
        self._update_status_icon("ready")  # Иконка готовности
        self.status_bar.addPermanentWidget(self.status_icon, stretch=0)
        
        # Индикатор прогресса (справа) — скрыт по умолчанию
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(PROGRESSBAR_STYLE)
        self.status_bar.addPermanentWidget(self.progress_bar, stretch=0)

        # Метка времени (справа)
        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px; padding: 0px 8px;")
        self.status_bar.addPermanentWidget(self.time_label, stretch=0)
        
        # Индикатор режима (PostgreSQL / Файловый)
        self.mode_indicator = QLabel()
        self.mode_indicator.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px; padding: 0px 8px;")
        self.status_bar.addPermanentWidget(self.mode_indicator, stretch=0)
        self._update_mode_indicator()
        
        # Таймер для обновления времени
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()

        # Инициализация иконки статуса
        self._update_status_icon('db' if self.repository_switcher.mode == 'postgres' else 'file')

    def _on_upload_info_requested(self, parser):
        """Перейти на экран информации о загрузке."""
        self.parser = parser
        self.current_file = self.home_screen.current_file
        
        # Получаем метрики турбины
        metrics = parser.get_turbine_metrics()
        
        # Собираем информацию о загруженных датчиках и файлах
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
        
        # Формируем данные для отображения
        turbine_name = self._extract_wtg_from_path(self.current_file) if self.current_file else "Неизвестная"
        generator_speed = f"{metrics.get('generator_speed_rpm', 0):.0f} RPM" if metrics.get('generator_speed_rpm') else ""
        active_power = f"{metrics.get('power_kw', 0):.0f} KW" if metrics.get('power_kw') else ""
        
        # Получаем record_number и record_datetime из метаданных парсера
        record_number = ""
        record_datetime = ""
        if hasattr(parser, 'turbine_metadata') and parser.turbine_metadata:
            record_number = str(parser.turbine_metadata.get('record_number', ''))[:5]
            record_datetime = parser.turbine_metadata.get('record_datetime', '')
        
        # Получаем длину записи из метаданных
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

        # === СРАЗУ загружаем данные в RawDataScreen и AnalysisDataScreen ===
        self._prepare_raw_data()
        self.analysis_screen.set_parser(self.parser)

        self.tabs.setCurrentWidget(self.upload_info_screen)
        self.status_icon.setToolTip(
            f"Загружено: {Path(self.current_file).name if self.current_file else 'файл'}"
        )

    def _prepare_raw_data(self):
        """Подготовить данные для экрана сырых данных."""
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
                        'name': SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}")
                    }
        
        self.raw_data_screen.set_sensor_data(raw_sensor_data)

    def _on_upload_info_back(self):
        """Вернуться на Home из экрана информации."""
        self.tabs.setCurrentWidget(self.home_screen)

    def _on_upload_info_process(self):
        """Перейти к экрану сырых данных."""
        if not self.parser:
            return
        
        # Собираем данные для raw_data_screen
        raw_sensor_data = {}
        available_sensors = self.parser.get_available_sensors()
        
        # Отладочный лог
        import tempfile, datetime
        log_path = Path(tempfile.gettempdir()) / "vibrodiag_debug.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== Debug log {datetime.datetime.now()} ===\n")
            f.write(f"Available sensors: {available_sensors}\n")
            
            for sensor_id in range(1, 9):
                data = self.parser.get_sensor_data(sensor_id)
                if data:
                    f.write(f"Sensor {sensor_id} data keys: {list(data.keys())}\n")
                    
                    # Берём первый доступный сигнал для отображения
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
                            'name': SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}")
                        }
                else:
                    f.write(f"Sensor {sensor_id}: no data\n")
            
            f.write(f"Total sensors with data: {list(raw_sensor_data.keys())}\n")
        
        self.raw_data_screen.set_sensor_data(raw_sensor_data)
        self.tabs.setCurrentWidget(self.raw_data_screen)
        self.status_icon.setToolTip("Просмотр сырых данных")

    def _on_raw_data_back(self):
        """Вернуться на экран информации из сырых данных."""
        self.tabs.setCurrentWidget(self.upload_info_screen)

    def _on_raw_data_analyze(self):
        """Перейти к анализу данных из экрана сырых данных."""
        if self.parser is None:
            return
        self.analysis_screen.set_parser(self.parser)
        self.tabs.setCurrentWidget(self.analysis_screen)
        available = self.parser.get_available_sensors()
        self.status_icon.setToolTip(
            f"Анализ: {Path(self.current_file).name if self.current_file else 'файл'} | Датчики: {available}"
        )

    def setup_menu(self):
        """Настроить меню."""
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

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        open_action = QAction("Открыть архив...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_archive)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Меню Экспорт
        export_menu = file_menu.addMenu("Экспорт")

        export_csv_action = QAction("CSV...", self)
        export_csv_action.triggered.connect(self._export_csv_from_menu)
        export_menu.addAction(export_csv_action)

        export_excel_action = QAction("Excel...", self)
        export_excel_action.triggered.connect(self._export_excel_from_menu)
        export_menu.addAction(export_excel_action)

        export_pdf_action = QAction("PDF-отчёт...", self)
        export_pdf_action.triggered.connect(self._export_pdf_from_menu)
        export_menu.addAction(export_pdf_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Анализ
        analysis_menu = menubar.addMenu("Анализ")

        trends_action = QAction("График трендов", self)
        trends_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.trends_screen))
        analysis_menu.addAction(trends_action)

        # Меню Настройки
        settings_menu = menubar.addMenu("Настройки")

        settings_action = QAction("Настройки приложения...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        """Показать диалог «О программе»."""
        mode_text = "PostgreSQL" if settings.use_database else "Файловая система"
        show_about(
            self,
            "О программе",
            f"<h2>SMP12C VibroDiag Analyzer</h2>"
            f"<p><b>Версия:</b> {settings.app_version}</p>"
            f"<p><b>Режим хранения:</b> {mode_text}</p>"
            f"<p>Система анализа вибрационной диагностики ветротурбин</p>"
            f"<p><b>Разработано:</b> A.Telezhenko, 2026</p>"
            f"<p><b>Стандарты:</b> ISO 10816-21:2015, ГОСТ 10816-21-2021</p>"
        )

    def _on_connection_success(self, info: str):
        """Обработка успешного подключения."""
        logger.info(info)
        self._update_mode_indicator()

    def _on_connection_failed(self, error: str):
        """Обработка ошибки подключения."""
        logger.error(error)
        show_warning(self, "Ошибка подключения", error)
        self._update_mode_indicator()

    def _on_mode_changed(self, mode: str):
        """Обработка смены режима."""
        self._update_status_icon('db' if mode == 'postgres' else 'file')
        self._update_mode_indicator()
        
        # Пересоздаём сервисы
        self.persistence_service = None
        self.auto_scan_service = None
        if mode == 'postgres':
            self._init_db_services()
        
        # Обновляем HomeScreen
        self.home_screen.set_repository(self.repository_switcher.repository)
        self.home_screen.persistence_service = self.persistence_service
        self.home_screen.auto_scan_service = self.auto_scan_service
        
        # Обновляем TrendsScreen
        self.trends_screen.repository = self.repository_switcher.repository
        
        # Обновляем UploadInfoScreen
        self.upload_info_screen.repository = self.repository_switcher.repository

    def _update_mode_indicator(self):
        """Обновить индикатор режима в статус-баре."""
        info = self.repository_switcher.get_repository_info()
        if info['mode'] == 'postgres':
            text = f"Режим: PostgreSQL ({info.get('host', 'localhost')})"
            color = "#448AFF"
        else:
            text = "Режим: Файловая система"
            color = "#888888"
        
        self.mode_indicator.setText(text)
        self.mode_indicator.setStyleSheet(
            f"color: {color}; font-size: 10px; padding: 0px 8px;"
        )

    def _open_settings(self):
        """Открыть диалог настроек."""
        dialog = SettingsDialog(self, repository_switcher=self.repository_switcher)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.archives_found.connect(self.home_screen.add_archives)
        dialog.switch_to_home.connect(lambda: self.tabs.setCurrentIndex(0))
        dialog.exec()

    def _on_settings_changed(self):
        """Обработчик изменения настроек (динамическое применение)."""
        self._update_mode_indicator()
        show_info(
            self,
            "Настройки применены",
            "Изменения настроек применены."
        )

    def _update_time(self):
        """Обновить время в статус-баре."""
        from datetime import datetime
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _update_status_icon(self, state: str):
        """Обновить иконку статус-бара."""
        icons = {
            'ready': ('mdi.check-circle', '#00C853'),      # Зелёная — готово
            'loading': ('mdi.loading', '#FFC107'),          # Жёлтая — загрузка
            'error': ('mdi.alert-circle', '#DD2C00'),       # Красная — ошибка
            'db': ('mdi.database', '#448AFF'),              # Синяя — БД
            'file': ('mdi.folder', '#888888'),              # Серая — файлы
        }
        icon_name, color = icons.get(state, icons['ready'])
        pixmap = qta.icon(icon_name, color=color).pixmap(16, 16)
        self.status_icon.setPixmap(pixmap)
        self.status_icon.setToolTip(
            "Готово к работе" if state == 'ready' else
            "Загрузка..." if state == 'loading' else
            "Ошибка" if state == 'error' else
            "Режим: PostgreSQL" if state == 'db' else
            "Режим: Файловая система" if state == 'file' else ""
        )

    def show_status_message(self, message: str, icon_name: str = "mdi.info", duration_ms: int = 5000):
        """
        Показать сообщение в статус-баре с иконкой.
        
        Args:
            message: Текст сообщения
            icon_name: Иконка QtAwesome (например, "mdi.info", "mdi.check-circle")
            duration_ms: Время отображения в миллисекундах (по умолчанию 5000)
        """
        self.status_bar.showMessage(message, duration_ms)
        
        # Временно меняем иконку
        old_icon = self.status_icon.toolTip()
        pixmap = qta.icon(icon_name, color='#448AFF').pixmap(16, 16)
        self.status_icon.setPixmap(pixmap)
        self.status_icon.setToolTip(message)
        
        # Возвращаем иконку через таймер
        QTimer.singleShot(duration_ms, lambda: self._update_status_icon(
            'db' if settings.use_database else 'file'
        ))

    def show_progress(self, message: str = "Загрузка..."):
        """Показать индикатор прогресса."""
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        self.progress_bar.setVisible(True)
        self._update_status_icon('loading')

    def hide_progress(self, message: str = "Готов к работе"):
        """Скрыть индикатор прогресса."""
        self.progress_bar.setVisible(False)
        self._update_status_icon('db' if settings.use_database else 'file')

    def set_progress_value(self, value: int, max_value: int = 100):
        """Установить значение прогресса (0-100)."""
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(value)
        self.progress_bar.setVisible(True)
        self._update_status_icon('loading')

    def apply_styles(self):
        """Применить стили (закомментировано для чёрно-белой темы Home)."""
        # self.setStyleSheet(STYLESHEET)

        # Глобальная тёмная тема для QFileDialog
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
        """Извлечь WTG из пути к файлу."""
        import re
        match = re.search(r'WTG(\d{1,2})', Path(path).name, re.IGNORECASE)
        if match:
            return f"WTG{int(match.group(1))}"
        return "Неизвестная"

    def load_archive(self):
        """Загрузить архив с данными (через меню Файл)."""
        self.home_screen._load_archive()

    def _export_csv_from_menu(self):
        """Экспорт в CSV из меню."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_csv()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "Нет данных", "Сначала загрузите файл для анализа.")

    def _export_excel_from_menu(self):
        """Экспорт в Excel из меню."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_excel()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "Нет данных", "Сначала загрузите файл для анализа.")

    def _export_pdf_from_menu(self):
        """Экспорт в PDF из меню."""
        if self.analysis_screen.parser:
            self.analysis_screen._export_pdf()
        else:
            from .styled_message_box import show_warning
            show_warning(self, "Нет данных", "Сначала загрузите файл для анализа.")

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        reply = show_question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите закрыть приложение?"
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
