"""Главное окно приложения"""

import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTabWidget,
    QLabel, QStatusBar, QMenuBar, QMenu, QAction,
    QScrollArea, QFrame
)
from .styled_message_box import show_warning, show_about
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QFont, QPixmap

from .canvas import MplCanvas
from .upload_info_screen import UploadInfoScreen, SENSOR_DESCRIPTIONS
from .raw_data_screen import RawDataScreen
from smp12c_vibrodiag.parsers.rd2_parser import process_rd2_file
from smp12c_vibrodiag.utils.file_handler import FileHandler

from PyQt5.QtWidgets import QApplication


class MainWindow(QMainWindow):
    """Главное окно приложения SMP12C VibroDiag"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SMP12C VibroDiag Analyzer')
        self.setGeometry(100, 100, 1400, 900)
        
        self._temp_dirs: List[Path] = []  # Временные директории для ZIP
        self._current_results: Dict[str, dict] = {}  # Результаты обработки
        self._file_queue: List[str] = []  # Очередь файлов для загрузки
        
        # Данные для новых экранов
        self._loaded_sensors: Dict[int, dict] = {}  # sensor_id -> result
        self._turbine_name: str = "Неизвестная ВЭУ"
        self._current_source: str = ""  # Имя файла или архива
        
        # Экранные виджеты
        self._upload_info_screen: Optional[UploadInfoScreen] = None
        self._raw_data_screen: Optional[RawDataScreen] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        # Центральное виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главная вертикальная раскладка
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Верхняя панель с кнопками
        btn_layout = QHBoxLayout()
        
        # Кнопка загрузки .rd2 файлов
        self.btn_load_rd2 = QPushButton('Загрузить .RD2')
        self.btn_load_rd2.clicked.connect(self._load_rd2_files)
        self.btn_load_rd2.setFixedWidth(150)
        btn_layout.addWidget(self.btn_load_rd2)
        
        # Кнопка загрузки ZIP
        self.btn_load_zip = QPushButton('Загрузить ZIP')
        self.btn_load_zip.clicked.connect(self._load_zip_archive)
        self.btn_load_zip.setFixedWidth(150)
        btn_layout.addWidget(self.btn_load_zip)
        
        # Кнопка обработки
        self.btn_process = QPushButton('Обработать')
        self.btn_process.clicked.connect(self._process_files)
        self.btn_process.setFixedWidth(150)
        self.btn_process.setEnabled(False)
        btn_layout.addWidget(self.btn_process)
        
        # Кнопка сохранения
        self.btn_save = QPushButton('Сохранить график')
        self.btn_save.clicked.connect(self._save_graph)
        self.btn_save.setFixedWidth(150)
        btn_layout.addWidget(self.btn_save)
        
        # Прокрастель
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout)
        
        # Вкладочный виджет для графиков
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        main_layout.addWidget(self.tab_widget)
        
        # Статусная строка
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Готов')
        
        # Меню
        self._create_menu()
        
        # Приветственная вкладка
        self._create_welcome_tab()
    
    def _create_menu(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu('Файл')
        
        load_rd2_action = QAction('Открыть .RD2...', self)
        load_rd2_action.triggered.connect(self._load_rd2_files)
        file_menu.addAction(load_rd2_action)
        
        load_zip_action = QAction('Открыть ZIP...', self)
        load_zip_action.triggered.connect(self._load_zip_archive)
        file_menu.addAction(load_zip_action)
        
        file_menu.addSeparator()
        
        save_action = QAction('Сохранить график как...', self)
        save_action.triggered.connect(self._save_graph)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню О программе
        help_menu = menubar.addMenu('Справка')
        
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_welcome_tab(self):
        """Создание приветственной вкладки"""
        welcome_widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Заголовок
        title_label = QLabel('SMP12C VibroDiag Analyzer')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ff69b4;
            padding: 20px;
        """)
        layout.addWidget(title_label)
        
        # Картинка редуктора
        try:
            img_label = QLabel()
            pixmap = QPixmap('D:/Сoding/pyton_pro/img/app_interface04.png')
            if not pixmap.isNull():
                img_label.setPixmap(pixmap.scaled(
                    600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                img_label.setScaledContents(True)
                img_label.setAlignment(Qt.AlignCenter)
                img_label.setStyleSheet("background-color: transparent;")
                layout.addWidget(img_label)
            else:
                # Если картинка не найдена, показываем текстовое сообщение
                info_label = QLabel('[+] Вибродиагностика ветротурбин [+]')
                info_label.setAlignment(Qt.AlignCenter)
                info_label.setStyleSheet("font-size: 20px; color: #ff69b4; padding: 20px;")
                layout.addWidget(info_label)
        except Exception as e:
            # Если картинка не найдена, показываем текстовое сообщение
            info_label = QLabel('[+] Вибродиагностика ветротурбин [+]')
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("font-size: 20px; color: #ff69b4; padding: 20px;")
            layout.addWidget(info_label)
        
        # Информация
        info_text = """
        <table style="color: #e0e0e0; font-size: 13px; line-height: 1.8;">
        <tr><td style="color: #ff69b4;">[+] Поддерживаемые форматы:</td></tr>
        <tr><td>  * .rd2, .rw2 (файлы вибродиагностики)</td></tr>
        <tr><td>  * .zip (архивы с .rd2 файлами)</td></tr>
        <tr><td style="color: #ff69b4; padding-top: 10px;">[+] Методы анализа:</td></tr>
        <tr><td>  * Расчёт СКЗ (RMS)</td></tr>
        <tr><td>  * FFT спектральный анализ</td></tr>
        <tr><td>  * Зонирование по ISO 10816</td></tr>
        <tr><td style="color: #ff69b4; padding-top: 10px;">[+] Зоны состояния:</td></tr>
        <tr><td>  <span style="color: #00ff00;">Zone A</span> < 2.3 мм/с -- Хорошо</td></tr>
        <tr><td>  <span style="color: #ffa500;">Zone B</span> 2.3-4.5 мм/с -- Удовлетворительно</td></tr>
        <tr><td>  <span style="color: #ff6600;">Zone C</span> 4.5-7.8 мм/с -- Неудовлетворительно</td></tr>
        <tr><td>  <span style="color: #ff0000;">Zone D</span> > 7.8 мм/с -- Критично</td></tr>
        </table>
        """
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label)
        
        # Инструкция
        instruction_label = QLabel('Нажмите "Загрузить .RD2" или "Загрузить ZIP" для начала анализа')
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("color: #666666; font-style: italic; padding: 20px;")
        layout.addWidget(instruction_label)
        
        welcome_widget.setLayout(layout)
        
        self.tab_widget.addTab(welcome_widget, ' Home ')
    
    def _load_rd2_files(self):
        """Загрузка .rd2 файлов"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            'Выберите файлы вибродиагностики',
            '',
            'RD2/RW2 Files (*.rd2 *.rw2);;All Files (*)'
        )
        
        if file_names:
            self._file_queue = list(file_names)
            self._current_source = "Файлы"
            
            # Обработка файлов для получения данных датчиков
            self._process_file_queue_for_upload()
    
    def _load_zip_archive(self):
        """Загрузка ZIP архива"""
        zip_file, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите ZIP архив',
            '',
            'ZIP Archives (*.zip);;All Files (*)'
        )
    
        if zip_file:
            # Распаковка во временную директорию
            temp_dir = FileHandler.get_temp_directory()
            self._temp_dirs.append(Path(temp_dir))
            
            FileHandler.unzip(zip_file, temp_dir)
            
            # Поиск .rd2 файлов
            rd2_files = FileHandler.find_rd2_files(temp_dir)
            
            if rd2_files:
                self._file_queue = rd2_files
                self._current_source = Path(zip_file).stem
                self._turbine_name = self._extract_turbine_name(Path(zip_file).stem)
                
                # Обработка файлов для получения данных датчиков
                self._process_file_queue_for_upload()
            else:
                self.statusBar.showMessage('В архиве не найдено .rd2 файлов')
    
    def _add_file_to_queue(self, filepath: str):
        """Добавление файла в очередь обработки"""
        self._current_results[filepath] = None
    
    def _extract_turbine_name(self, source_name: str) -> str:
        """
        Извлечение имени ВЭУ из имени файла
        
        Args:
            source_name: имя файла или архива
            
        Returns:
            Название ветротурбины (например, WTG06)
        """
        import re
        
        # Поиск паттерна WTGxx или WTG-xx
        match = re.search(r'(WTG-?\d+)', source_name, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        # Поиск паттерна ВЭУxx или ветротурбинаxx
        match = re.search(r'(ВЭУ\d+)', source_name)
        if match:
            return match.group(1)
        
        # Если ничего не найдено, возвращаем первое слово
        return source_name.split('_')[0] if '_' in source_name else source_name
    
    def _process_file_queue_for_upload(self):
        """
        Обработка очереди файлов для экрана информации о загрузке
        Парсит файлы и собирает данные датчиков
        """
        self.statusBar.showMessage('Анализ файлов...')
        QCoreApplication.processEvents()
        
        self._loaded_sensors = {}
        self._sensor_file_paths = {}  # sensor_id -> список путей к файлам
        
        for filepath in self._file_queue:
            try:
                result = process_rd2_file(filepath)
                
                # Определение номера датчика из имени файла
                sensor_id = self._extract_sensor_id(Path(filepath).name)
                
                if sensor_id and 1 <= sensor_id <= 8:
                    self._loaded_sensors[sensor_id] = result
                    
                    # Сохраняем путь к файлу
                    if sensor_id not in self._sensor_file_paths:
                        self._sensor_file_paths[sensor_id] = []
                    self._sensor_file_paths[sensor_id].append(filepath)
                    
                    # Извлечение имени ВЭУ из первого файла
                    if self._turbine_name == "Неизвестная ВЭУ":
                        turbine_from_file = result['metadata'].get('turbine_id', '')
                        if turbine_from_file:
                            self._turbine_name = turbine_from_file
                else:
                    # Если номер датчика не определён, используем sensor_id из метаданных
                    meta_sensor = result['metadata'].get('sensor_id')
                    if meta_sensor and 1 <= meta_sensor <= 8:
                        self._loaded_sensors[meta_sensor] = result
                        if meta_sensor not in self._sensor_file_paths:
                            self._sensor_file_paths[meta_sensor] = []
                        self._sensor_file_paths[meta_sensor].append(filepath)
                    
            except Exception as e:
                self.statusBar.showMessage(f'Ошибка обработки {Path(filepath).name}: {str(e)[:50]}')
        
        # Показ экрана информации о загрузке
        self._show_upload_info_screen()
    
    def _extract_sensor_id(self, filename: str) -> Optional[int]:
        """
        Извлечение номера датчика из имени файла
        
        Args:
            filename: имя файла (например, SENSOR_01_LOW_W.rd2)
            
        Returns:
            Номер датчика или None
        """
        import re
        
        # Поиск паттерна SENSOR_XX
        match = re.search(r'SENSOR[_\s]?(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Поиск паттерна _XX_ в имени
        match = re.search(r'[_\-](\d{2})[_\-]', filename)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 8:
                return num
        
        return None
    
    def _process_files(self):
        """Обработка всех загруженных файлов"""
        if not self._current_results:
            show_warning(self, 'Ошибка', 'Нет файлов для обработки')
            return
        
        self.statusBar.showMessage('Обработка...')
        QApplication.processEvents()
        
        processed_count = 0
        
        for filepath in list(self._current_results.keys()):
            try:
                result = process_rd2_file(filepath)
                self._current_results[filepath] = result
                self._create_result_tab(filepath, result)
                processed_count += 1
            except Exception as e:
                show_warning(
                    self, 
                    f'Ошибка обработки {Path(filepath).name}',
                    str(e)
                )
        
        self.statusBar.showMessage(f'Обработано файлов: {processed_count}')
    
    def _show_upload_info_screen(self):
        """Показ экрана информации о загрузке"""
        # Удаляем все вкладки кроме приветственной
        while self.tab_widget.count() > 1:
            self.tab_widget.removeTab(1)
        
        # Сбор данных о файлах по датчикам
        sensor_files = {}
        generator_speed = ""
        active_power = ""
        record_length = ""
        record_number = ""
        record_datetime = ""
        
        # Используем _sensor_file_paths для получения путей к файлам
        for sensor_id, filepaths in self._sensor_file_paths.items():
            for filepath in filepaths:
                filename = Path(filepath).name
                
                # Определение типа файла (FILTER, HIGH, LOW)
                file_type = ""
                if "FILTER" in filename.upper():
                    file_type = "FILTER"
                elif "HIGH" in filename.upper():
                    file_type = "HIGH"
                elif "LOW" in filename.upper():
                    file_type = "LOW"
                
                if sensor_id not in sensor_files:
                    sensor_files[sensor_id] = {}
                if file_type:
                    sensor_files[sensor_id][file_type] = filepath
            
        # Извлечение метаданных из первого загруженного датчика
        if self._loaded_sensors:
            first_sensor_id = list(self._loaded_sensors.keys())[0]
            result = self._loaded_sensors[first_sensor_id]
            if result.get('metadata'):
                meta = result['metadata']
                generator_speed = meta.get('generator_speed', '')
                active_power = meta.get('active_power', '')
                record_length = meta.get('record_length', '')
                record_number = meta.get('record_number', '')
                record_datetime = meta.get('record_datetime', '')
        
        # Создаем экран информации
        self._upload_info_screen = UploadInfoScreen()
        self._upload_info_screen.set_upload_data(
            turbine_name=self._turbine_name,
            loaded_sensors=self._loaded_sensors,
            sensor_files=sensor_files,
            generator_speed=generator_speed,
            active_power=active_power,
            record_length=record_length,
            record_number=record_number,
            record_datetime=record_datetime
        )
        self._upload_info_screen.set_callbacks(
            on_back=self._on_upload_info_back,
            on_process=self._on_upload_info_process
        )
        
        self.tab_widget.addTab(self._upload_info_screen, ' Информация ')
        self.tab_widget.setCurrentWidget(self._upload_info_screen)
        
        self.statusBar.showMessage(f'Загружено датчиков: {len(self._loaded_sensors)} из 8')
    
    def _on_upload_info_back(self):
        """Возврат к приветственной странице"""
        self.tab_widget.setCurrentIndex(0)
        self.statusBar.showMessage('Готов')
    
    def _on_upload_info_process(self):
        """Переход к экрану сырых данных"""
        self._show_raw_data_screen()
    
    def _show_raw_data_screen(self):
        """Показ экрана сырых данных"""
        # Подготовка данных для графиков
        sensor_raw_data = {}
        
        for sensor_id, result in self._loaded_sensors.items():
            try:
                # Извлечение временного ряда из raw_data
                raw_data = result.get('raw_data', {})
                time_data = raw_data.get('timestamps', np.array([]))
                signal_data = raw_data.get('values', np.array([]))
                
                # Если данных нет, пробуем альтернативные ключи
                if len(time_data) == 0:
                    time_data = result.get('timestamps', np.array([]))
                if len(signal_data) == 0:
                    signal_data = result.get('values', np.array([]))
                
                if len(time_data) > 0 and len(signal_data) > 0:
                    sensor_raw_data[sensor_id] = {
                        'time': time_data,
                        'signal': signal_data,
                        'name': result['metadata'].get('sensor_name', 
                                SENSOR_DESCRIPTIONS.get(sensor_id, f"Датчик {sensor_id}"))
                    }
            except Exception as e:
                self.statusBar.showMessage(f'Ошибка подготовки данных датчика {sensor_id}: {str(e)[:30]}')
        
        # Удаляем экран информации и показываем сырые данные
        if self._upload_info_screen:
            index = self.tab_widget.indexOf(self._upload_info_screen)
            if index > 0:
                self.tab_widget.removeTab(index)
        
        # Создаем экран сырых данных
        self._raw_data_screen = RawDataScreen()
        self._raw_data_screen.set_sensor_data(sensor_raw_data)
        self._raw_data_screen.set_back_callback(self._on_raw_data_back)
        
        self.tab_widget.addTab(self._raw_data_screen, ' Сырые данные ')
        self.tab_widget.setCurrentWidget(self._raw_data_screen)
        
        self.statusBar.showMessage(f'Отображено датчиков: {len(sensor_raw_data)}')
    
    def _on_raw_data_back(self):
        """Возврат к экрану информации"""
        if self._raw_data_screen:
            index = self.tab_widget.indexOf(self._raw_data_screen)
            if index >= 0:
                self.tab_widget.removeTab(index)
        
        # Возвращаем экран информации
        if self._upload_info_screen:
            self.tab_widget.addTab(self._upload_info_screen, ' Информация ')
            self.tab_widget.setCurrentWidget(self._upload_info_screen)
    
    def _create_result_tab(self, filepath: str, result: dict):
        """Создание вкладки с результатами"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        # Информация о файле
        info_label = QLabel(
            f"Турбина: {result['metadata']['turbine_id']} | "
            f"Датчик: {result['metadata']['sensor_name']} | "
            f"Зона: {result['zone']} | "
            f"СКЗ: {result['rms']['total_rms']:.3f} мм/с"
        )
        info_label.setFont(QFont('Verdana', 9))
        layout.addWidget(info_label)
        
        # График
        canvas = MplCanvas(self, width=10, height=5, dpi=100)
        canvas.plot_spectrum(
            result['spectrum']['frequencies'],
            result['spectrum']['amplitudes'],
            result['zone'],
            result['rms']['total_rms']
        )
        
        # Callback для клика
        def on_click(x, y):
            self.statusBar.showMessage(f'Частота: {x:.2f} Гц, Амплитуда: {y:.6f} мм/с')
        
        canvas.set_click_callback(on_click)
        
        layout.addWidget(canvas)
        
        tab_widget.setLayout(layout)
        
        # Название вкладки
        tab_name = Path(filepath).stem
        if len(tab_name) > 20:
            tab_name = tab_name[:17] + '...'
        
        self.tab_widget.addTab(tab_widget, tab_name)
        self.tab_widget.setCurrentWidget(tab_widget)
    
    def _close_tab(self, index: int):
        """Закрытие вкладки"""
        if index > 0:  # Не закрывать приветственную вкладку
            widget = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            
            # Если осталась только приветственная вкладка
            if self.tab_widget.count() == 1:
                self.statusBar.showMessage('Готов')
    
    def _on_tab_changed(self, index: int):
        """Обработка смены вкладки"""
        if index == 0:
            self.statusBar.showMessage('Готов')
    
    def _save_graph(self):
        """Сохранение текущего графика"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index <= 0:
            show_warning(self, 'Ошибка', 'Нет графика для сохранения')
            return
        
        widget = self.tab_widget.widget(current_index)
        canvas = widget.findChild(MplCanvas)
        
        if not canvas:
            show_warning(self, 'Ошибка', 'График не найден')
            return
        
        # Диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Сохранить график',
            '',
            'PNG Images (*.png);;All Files (*)'
        )
        
        if file_path:
            if not file_path.endswith('.png'):
                file_path += '.png'
            
            fig = canvas.fig
            success = FileHandler.save_graph(fig, file_path)
            
            if success:
                self.statusBar.showMessage(f'График сохранён: {file_path}')
            else:
                show_warning(self, 'Ошибка', 'Не удалось сохранить график')
    
    def _show_about(self):
        """О программе"""
        show_about(
            self,
            'О программе',
            'SMP12C VibroDiag Analyzer v1.0.0\n\n'
            'Приложение для анализа вибрационной диагностики\n'
            'ветротурбин системы SMP12C (Siemens Gamesa)\n\n'
            'Технологии: Python, PyQt5, matplotlib, numpy'
        )
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Очистка временных файлов
        for temp_dir in self._temp_dirs:
            try:
                FileHandler.cleanup_temp_directory(str(temp_dir))
            except:
                pass
        
        event.accept()
