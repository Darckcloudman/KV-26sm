# -*- coding: utf-8 -*-
"""
Диалог настроек приложения KWF Prometheus v1.4
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QFileDialog, QFrame, QProgressBar, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_BORDER, COLOR_ACCENT, COLOR_ACCENT_HOVER,
    BUTTON_STYLE, BUTTON_SMALL_STYLE
)
from ..dal.config import settings
from ..dal.logger import get_logger

logger = get_logger(__name__)


class ModuleStatusIndicator(QFrame):
    """Индикатор статуса модуля."""

    def __init__(self, name: str, description: str, is_critical: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_TERTIARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Индикатор (кружок)
        self.status_dot = QFrame()
        self.status_dot.setFixedSize(16, 16)
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: #00C853;
                border-radius: 8px;
            }}
        """)
        layout.addWidget(self.status_dot)

        # Информация
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-size: 12px;
            font-weight: bold;
        """)
        info_layout.addWidget(name_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            color: {COLOR_TEXT_TERTIARY};
            font-size: 10px;
        """)
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, stretch=1)

        # Критичность
        if is_critical:
            crit_label = QLabel("КРИТИЧНЫЙ")
            crit_label.setStyleSheet("""
                color: #DD2C00;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 6px;
                background-color: rgba(221, 44, 0, 0.2);
                border-radius: 2px;
            """)
            layout.addWidget(crit_label)

    def set_status(self, ok: bool):
        """Установить статус модуля."""
        color = "#00C853" if ok else "#DD2C00"
        self.status_dot.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
            }}
        """)


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""

    settings_changed = Signal()  # Сигнал изменения настроек

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self._setup_ui()
        self._load_settings()
        self._check_modules()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title = QLabel("Настройки приложения")
        title.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-size: 18px;
            font-weight: bold;
            padding: 10px;
            border-bottom: 2px solid {COLOR_BORDER};
        """)
        layout.addWidget(title)

        # Табы
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                background-color: {COLOR_BG_SECONDARY};
            }}
            QTabBar::tab {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_SECONDARY};
                padding: 8px 16px;
                border: none;
                font-size: 11px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_BG_SECONDARY};
                color: {COLOR_TEXT_PRIMARY};
                border-bottom: 2px solid {COLOR_ACCENT};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLOR_BG_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(self.tabs, stretch=1)

        # Вкладка 1: База данных
        db_widget = self._create_database_tab()
        self.tabs.addTab(db_widget, "База данных")

        # Вкладка 2: Хранилище
        storage_widget = self._create_storage_tab()
        self.tabs.addTab(storage_widget, "Хранилище")

        # Вкладка 3: Логирование
        log_widget = self._create_logging_tab()
        self.tabs.addTab(log_widget, "Логирование")

        # Вкладка 4: Модули
        modules_widget = self._create_modules_tab()
        self.tabs.addTab(modules_widget, "Модули")

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet(BUTTON_STYLE)
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("✖ Отмена")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_BG_SECONDARY};
                color: {COLOR_TEXT_PRIMARY};
            }}
        """)
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _create_database_tab(self) -> QWidget:
        """Создать вкладку настроек БД."""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Хост
        self.db_host_input = QLineEdit()
        self.db_host_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Хост PostgreSQL:", self.db_host_input)

        # Порт
        self.db_port_input = QSpinBox()
        self.db_port_input.setRange(1, 65535)
        self.db_port_input.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Порт:", self.db_port_input)

        # Пользователь
        self.db_user_input = QLineEdit()
        self.db_user_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Пользователь:", self.db_user_input)

        # База данных
        self.db_name_input = QLineEdit()
        self.db_name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("База данных:", self.db_name_input)

        # Ретраи
        self.db_retries_input = QSpinBox()
        self.db_retries_input.setRange(0, 10)
        self.db_retries_input.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Повторы подключения:", self.db_retries_input)

        # Задержка между ретраями
        self.db_retry_delay_input = QSpinBox()
        self.db_retry_delay_input.setRange(0, 30)
        self.db_retry_delay_input.setSuffix(" сек")
        self.db_retry_delay_input.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Задержка повтора:", self.db_retry_delay_input)

        # Использовать БД
        self.db_enabled_checkbox = QCheckBox("Использовать базу данных")
        self.db_enabled_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 11px;
            }}
        """)
        layout.addRow("", self.db_enabled_checkbox)

        return widget

    def _create_storage_tab(self) -> QWidget:
        """Создать вкладку настроек хранилища."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Путь
        path_label = QLabel("Путь к архивам:")
        path_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        layout.addWidget(path_label)
        
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        self.storage_path_input = QLineEdit()
        self.storage_path_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        path_layout.addWidget(self.storage_path_input, stretch=1)

        browse_btn = QPushButton("Обзор...")
        browse_btn.setStyleSheet(BUTTON_SMALL_STYLE)
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_storage_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Описание
        desc_label = QLabel(
            "Укажите путь к папке с ZIP-архивами данных вибродиагностики.\n"
            "Приложение будет сканировать эту папку для отображения доступных записей."
        )
        desc_label.setStyleSheet(f"""
            color: {COLOR_TEXT_TERTIARY};
            font-size: 10px;
            padding: 10px;
            background-color: {COLOR_BG_TERTIARY};
            border-radius: 4px;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()
        return widget

    def _create_logging_tab(self) -> QWidget:
        """Создать вкладку настроек логирования."""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Уровень логирования
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 11px;
            }}
        """)
        layout.addRow("Уровень логирования:", self.log_level_combo)

        # Лог в файл
        self.log_to_file_checkbox = QCheckBox("Записывать логи в файл (app.log)")
        self.log_to_file_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 11px;
            }}
        """)
        layout.addRow("", self.log_to_file_checkbox)

        # Лог в консоль
        self.log_to_console_checkbox = QCheckBox("Выводить логи в консоль")
        self.log_to_console_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLOR_TEXT_PRIMARY};
                font-size: 11px;
            }}
        """)
        layout.addRow("", self.log_to_console_checkbox)

        # Описание
        desc_label = QLabel(
            "Уровень логирования влияет на детализацию сообщений:\n"
            "• DEBUG — полная отладочная информация\n"
            "• INFO — основные события приложения\n"
            "• WARNING — предупреждения\n"
            "• ERROR — ошибки\n"
            "• CRITICAL — критические ошибки"
        )
        desc_label.setStyleSheet(f"""
            color: {COLOR_TEXT_TERTIARY};
            font-size: 10px;
            padding: 10px;
            background-color: {COLOR_BG_TERTIARY};
            border-radius: 4px;
        """)
        desc_label.setWordWrap(True)
        layout.addRow("", desc_label)

        return widget

    def _create_modules_tab(self) -> QWidget:
        """Создать вкладку статуса модулей."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title = QLabel("Статус критических модулей")
        title.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-size: 13px;
            font-weight: bold;
            padding: 5px;
        """)
        layout.addWidget(title)

        # Описание
        desc_label = QLabel(
            "Зелёный индикатор — модуль работает корректно.\n"
            "Красный индикатор — модуль недоступен или работает с ошибками."
        )
        desc_label.setStyleSheet(f"""
            color: {COLOR_TEXT_TERTIARY};
            font-size: 10px;
            padding: 8px;
            background-color: {COLOR_BG_TERTIARY};
            border-radius: 4px;
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Список модулей
        self.modules_layout = QVBoxLayout()
        self.modules_layout.setSpacing(6)
        layout.addLayout(self.modules_layout)

        layout.addStretch()
        return widget

    def _check_modules(self):
        """Проверить статус критических модулей."""
        # Очищаем старые индикаторы
        while self.modules_layout.count():
            item = self.modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Модули для проверки
        modules = [
            ("PySide6 / Qt", "Графический интерфейс", True),
            ("NumPy", "Математические вычисления", True),
            ("SciPy", "Сигнальная обработка (FFT)", True),
            ("pyqtgraph", "Отрисовка графиков", True),
            ("PostgreSQL", "База данных", False),
            ("asyncpg", "Асинхронный драйвер БД", False),
            ("SQLAlchemy", "ORM для БД", False),
            ("openpyxl", "Экспорт в Excel", False),
            ("reportlab", "Генерация PDF-отчётов", False),
        ]

        # Проверяем каждый модуль
        for name, desc, is_critical in modules:
            indicator = ModuleStatusIndicator(name, desc, is_critical)
            
            # Проверяем доступность
            ok = self._check_module(name)
            indicator.set_status(ok)
            
            self.modules_layout.addWidget(indicator)

    def _check_module(self, name: str) -> bool:
        """Проверить доступность модуля."""
        try:
            if name == "PySide6 / Qt":
                from PySide6.QtWidgets import QApplication
                return True
            elif name == "NumPy":
                import numpy
                return True
            elif name == "SciPy":
                import scipy
                return True
            elif name == "pyqtgraph":
                import pyqtgraph
                return True
            elif name == "PostgreSQL":
                # Проверяем подключение к БД
                return settings.use_database
            elif name == "asyncpg":
                import asyncpg
                return True
            elif name == "SQLAlchemy":
                import sqlalchemy
                return True
            elif name == "openpyxl":
                import openpyxl
                return True
            elif name == "reportlab":
                import reportlab
                return True
        except ImportError:
            return False
        
        return False

    def _browse_storage_path(self):
        """Выбрать путь к хранилищу."""
        path = QFileDialog.getExistingDirectory(
            self, "Выберите папку с архивами",
            self.storage_path_input.text() or ""
        )
        if path:
            self.storage_path_input.setText(path)

    def _load_settings(self):
        """Загрузить текущие настройки."""
        # База данных
        self.db_host_input.setText(settings.db_host)
        self.db_port_input.setValue(settings.db_port)
        self.db_user_input.setText(settings.db_user)
        self.db_name_input.setText(settings.db_name)
        self.db_retries_input.setValue(settings.db_connect_retries)
        self.db_retry_delay_input.setValue(settings.db_connect_retry_delay)
        self.db_enabled_checkbox.setChecked(settings.use_database)

        # Хранилище
        self.storage_path_input.setText(str(settings.archive_storage_path))

        # Логирование
        log_level = getattr(settings, 'log_level', 'INFO')
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        
        # Проверяем, включено ли логирование в файл/консоль
        # (это можно определить по наличию хендлеров в логгере)
        self.log_to_file_checkbox.setChecked(True)
        self.log_to_console_checkbox.setChecked(True)

    def _save_settings(self):
        """Сохранить настройки."""
        try:
            # Собираем новые настройки
            new_settings = {
                'db_host': self.db_host_input.text(),
                'db_port': self.db_port_input.value(),
                'db_user': self.db_user_input.text(),
                'db_name': self.db_name_input.text(),
                'db_connect_retries': self.db_retries_input.value(),
                'db_connect_retry_delay': self.db_retry_delay_input.value(),
                'use_database': self.db_enabled_checkbox.isChecked(),
                'archive_storage_path': self.storage_path_input.text(),
                'log_level': self.log_level_combo.currentText(),
            }

            # Сохраняем в .env файл
            from pathlib import Path
            env_path = Path(__file__).resolve().parent.parent.parent / ".env"
            
            if env_path.exists():
                # Читаем текущий .env
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Обновляем значения
                updated_lines = []
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in new_settings:
                            value = new_settings[key]
                            updated_lines.append(f"{key}={value}\n")
                            continue
                    updated_lines.append(line)

                # Записываем обновлённый .env
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(updated_lines)

            # Перезагружаем настройки
            from ..dal.config import Settings
            settings.__init__()

            # Сигнализируем об изменении
            self.settings_changed.emit()

            # Показываем сообщение
            from .styled_message_box import show_info
            show_info(self, "Настройки сохранены", 
                     "Изменения вступят в силу после перезапуска приложения.")

            self.accept()

        except Exception as e:
            from .styled_message_box import show_critical
            show_critical(self, "Ошибка сохранения", 
                         f"Не удалось сохранить настройки:\n{str(e)}")
