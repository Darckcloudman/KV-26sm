# -*- coding: utf-8 -*-
"""
Диалог настроек приложения KWF Prometheus v1.4.1

Возможности:
"""

import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox,
    QComboBox, QFileDialog, QFrame, QProgressBar, QCheckBox,
    QTextEdit, QPlainTextEdit, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSize
from PySide6.QtGui import QFont, QTextCursor, QIcon
import qtawesome as qta  # type: ignore[import-untyped]

from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_TEXT_DISABLED, COLOR_BORDER, COLOR_BORDER_SUBTLE,
    COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_ACCENT_PRESSED,
    BUTTON_STYLE, BUTTON_SMALL_STYLE, CHECKBOX_STYLE, LOG_TEXT_STYLE, SCROLLBAR_STYLE
)
from .styled_message_box import show_info, show_critical
from ..dal.config import settings
from ..dal.logger import get_logger
from ..dal.repository_switcher import RepositorySwitcher
from ..parsers.adaptive_archive_scanner import AdaptiveArchiveScanner, ArchiveCandidate

logger = get_logger(__name__)


class ScanWorker(QThread):
    """Поток для фонового сканирования хранилища."""
    
    log_message = Signal(str)           # HTML-сообщение для лога
    archive_found = Signal(object)      # ArchiveCandidate
    progress = Signal(int, int)         # current, total
    finished_scan = Signal(int, int, int)  # total, processed, errors
    error = Signal(str)
    
    def __init__(self, root_path: Path, parent=None):
        super().__init__(parent)
        self.root_path = Path(root_path)
        self._is_cancelled = False
    
    def cancel(self):
        """Отменить сканирование."""
        self._is_cancelled = True
    
    def _log(self, message: str, level: str = "INFO"):
        """Отправить сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        colors = {
            "INFO": "#BBBBBB",
            "SUCCESS": "#00C853",
            "WARNING": "#FFD600",
            "ERROR": "#DD2C00",
            "DEBUG": "#888888"
        }
        color = colors.get(level, "#BBBBBB")
        
        html = f'<span style="color:#666666;">[{timestamp}]</span> <span style="color:{color};">{message}</span>'
        self.log_message.emit(html)
    
    def run(self):
        """Запустить сканирование."""
        try:
            self._log(f"Начало сканирования хранилища: {self.root_path}", "INFO")
            
            if not self.root_path.exists():
                self._log(f"Корневой каталог не существует: {self.root_path}", "ERROR")
                self.error.emit(f"Каталог не найден: {self.root_path}")
                return
            
            scanner = AdaptiveArchiveScanner(self.root_path)
            
            total_found = 0
            processed = 0
            errors = 0
            
            def on_archive_found(candidate: ArchiveCandidate):
                nonlocal processed
                if self._is_cancelled:
                    return
                
                processed += 1
                size_mb = candidate.file_size_kb / 1024
                
                self._log(
                    f"Найден архив: {candidate.filename} "
                    f"(WTG={candidate.wtg_id or 'N/A'}, "
                    f"датчики={len(candidate.sensors_found)}, "
                    f"размер={size_mb:.1f} МБ)",
                    "SUCCESS"
                )
                
                if candidate.rd2_files_count > 0:
                    self._log(
                        f"  └─ Внутри: {candidate.rd2_files_count} файлов .rd2, "
                        f"датчики: {candidate.sensors_found}",
                        "DEBUG"
                    )
                
                if candidate.errors:
                    for err in candidate.errors:
                        self._log(f"  ⚠ {err}", "WARNING")
                
                self.archive_found.emit(candidate)
            
            def on_progress(current: int, total: int):
                if self._is_cancelled:
                    return
                self.progress.emit(current, total)
                if total > 0:
                    pct = current * 100 // total
                    if current % 10 == 0 or current == total:
                        self._log(f"Прогресс: {current}/{total} ({pct}%)", "DEBUG")
            
            def on_error(error_msg: str):
                nonlocal errors
                errors += 1
                self._log(error_msg, "ERROR")
            
            candidates = scanner.scan_with_callback(
                on_archive_found=on_archive_found,
                on_progress=on_progress,
                on_error=on_error
            )
            
            total_found = len(candidates)
            
            if self._is_cancelled:
                self._log("Сканирование отменено пользователем", "WARNING")
            else:
                self._log(
                    f"Сканирование завершено. "
                    f"Найдено архивов: {total_found}, "
                    f"обработано: {processed}, "
                    f"ошибок: {errors}",
                    "SUCCESS"
                )
            
            self.finished_scan.emit(total_found, processed, errors)
            
        except Exception as e:
            error_msg = f"Критическая ошибка сканирования: {e}"
            self._log(error_msg, "ERROR")
            self.error.emit(error_msg)
            self.finished_scan.emit(0, 0, 1)


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""

    settings_changed = Signal()  # Сигнал изменения настроек
    archives_found = Signal(list)  # Сигнал найденных архивов (список dict)
    switch_to_home = Signal()  # Сигнал перехода на вкладку Home

    def __init__(self, parent=None, repository_switcher: Optional[RepositorySwitcher] = None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(700, 550)
        self.setModal(True)
        
        self.repository_switcher = repository_switcher
        self._scan_worker: Optional[ScanWorker] = None

        # Задать тёмный фон диалогу
        self.setStyleSheet(f"""
            background-color: {COLOR_BG_SECONDARY};
        """)

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
            background-color: {COLOR_BG_SECONDARY};
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

    def _create_database_tab(self) -> QWidget:
        """Создать вкладку настроек БД."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Переключатель режима БД
        self.db_enabled_checkbox = QCheckBox("Использовать PostgreSQL")
        self.db_enabled_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.db_enabled_checkbox.stateChanged.connect(self._on_db_mode_changed)
        form_layout.addRow("Режим хранения:", self.db_enabled_checkbox)

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
        form_layout.addRow("Хост PostgreSQL:", self.db_host_input)

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
        form_layout.addRow("Порт:", self.db_port_input)

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
        form_layout.addRow("Пользователь:", self.db_user_input)

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
        form_layout.addRow("База данных:", self.db_name_input)

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
        form_layout.addRow("Повторы подключения:", self.db_retries_input)

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
        form_layout.addRow("Задержка повтора:", self.db_retry_delay_input)

        # Статус подключения
        self.db_status_label = QLabel("")
        self.db_status_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px;")
        form_layout.addRow("Статус:", self.db_status_label)

        layout.addLayout(form_layout)
        layout.addStretch()

        # Кнопки Применить/Отмена только для БД
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        apply_btn = QPushButton("Применить")
        apply_btn.setStyleSheet(BUTTON_STYLE)
        apply_btn.setFixedWidth(120)
        apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(f"""
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
        cancel_btn.setFixedWidth(120)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        return widget

    def _create_storage_tab(self) -> QWidget:
        """Создать вкладку настроек хранилища с логом сканирования."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # === 1. Лог сканирования + кнопка сохранения (ВВЕРХУ) ===
        log_header_layout = QHBoxLayout()
        
        log_label = QLabel("Лог сканирования:")
        log_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        log_header_layout.addWidget(log_label)
        
        log_header_layout.addStretch()
        
        # Кнопка сохранения лога
        self.save_log_btn = QPushButton("Сохранить лог")
        self.save_log_btn.setIcon(qta.icon('fa5.save', color='#000000', scale_factor=0.8))
        self.save_log_btn.setIconSize(QSize(18, 18))
        self.save_log_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_DISABLED};
            }}
        """)
        self.save_log_btn.setEnabled(False)
        self.save_log_btn.clicked.connect(self._save_scan_log)
        log_header_layout.addWidget(self.save_log_btn)
        
        layout.addLayout(log_header_layout)
        
        self.scan_log = QTextEdit()
        self.scan_log.setReadOnly(True)
        self.scan_log.setStyleSheet(LOG_TEXT_STYLE + SCROLLBAR_STYLE)
        self.scan_log.setMinimumHeight(200)
        self.scan_log.setPlaceholderText("Здесь будет отображаться подробный лог процесса сканирования...")
        layout.addWidget(self.scan_log, stretch=1)
        
        # === 2. Путь к хранилищу + Обзор (ПОСЕРЕДИНЕ) ===
        path_group = QHBoxLayout()
        
        path_label = QLabel("Путь к архивам:")
        path_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        path_group.addWidget(path_label)
        
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
        path_group.addWidget(self.storage_path_input, stretch=1)

        browse_btn = QPushButton("Обзор...")
        browse_btn.setIcon(qta.icon('mdi.folder-plus', color='#000000', scale_factor=0.8))
        browse_btn.setIconSize(QSize(18, 18))
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_DISABLED};
            }}
        """)
        browse_btn.setFixedWidth(100)
        browse_btn.clicked.connect(self._browse_storage_path)
        path_group.addWidget(browse_btn)

        layout.addLayout(path_group)

        # === 3. Кнопки сканирования + прогресс (ВНИЗУ) ===
        scan_layout = QHBoxLayout()
        
        # Кнопка "Сканировать" с иконкой QtAwesome mdi.folder-search
        self.scan_btn = QPushButton()
        self.scan_btn.setText("Сканировать")
        self.scan_btn.setIcon(qta.icon('mdi.folder-search', color='#000000', scale_factor=0.8))
        self.scan_btn.setIconSize(QSize(18, 18))
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_DISABLED};
            }}
        """)
        self.scan_btn.clicked.connect(self._start_scan)
        scan_layout.addWidget(self.scan_btn)

        # Кнопка "Отмена" с иконкой QtAwesome mdi.cancel
        self.scan_cancel_btn = QPushButton()
        self.scan_cancel_btn.setText("Отмена")
        self.scan_cancel_btn.setIcon(qta.icon('mdi.cancel', color='#000000', scale_factor=0.8))
        self.scan_cancel_btn.setIconSize(QSize(18, 18))
        self.scan_cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_DISABLED};
            }}
        """)
        self.scan_cancel_btn.setEnabled(False)
        self.scan_cancel_btn.clicked.connect(self._cancel_scan)
        scan_layout.addWidget(self.scan_cancel_btn)

        self.scan_progress = QProgressBar()
        self.scan_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLOR_BG_TERTIARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                text-align: center;
                color: {COLOR_TEXT_TERTIARY};
                font-size: 9px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 2px;
            }}
        """)
        self.scan_progress.setVisible(False)
        scan_layout.addWidget(self.scan_progress, stretch=1)

        scan_layout.addStretch()

        # Кнопка "Добавить в список" (активна после сканирования)
        self.add_to_list_btn = QPushButton("Добавить в список")
        self.add_to_list_btn.setIcon(qta.icon('ri.file-add-fill', color='#000000', scale_factor=0.8))
        self.add_to_list_btn.setIconSize(QSize(18, 18))
        self.add_to_list_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_DISABLED};
            }}
        """)
        self.add_to_list_btn.setEnabled(False)
        self.add_to_list_btn.clicked.connect(self._add_to_list)
        scan_layout.addWidget(self.add_to_list_btn)

        layout.addLayout(scan_layout)

        return widget

    def _create_logging_tab(self) -> QWidget:
        """Создать вкладку настроек логирования с просмотром логов."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- Верхняя панель: настройки ---
        settings_layout = QHBoxLayout()
        
        # Уровень логирования
        level_label = QLabel("Уровень логирования:")
        level_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        settings_layout.addWidget(level_label)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 100px;
            }}
        """)
        settings_layout.addWidget(self.log_level_combo)
        
        settings_layout.addSpacing(20)
        
        # Чек-боксы
        self.log_to_file_checkbox = QCheckBox("Записывать в файл")
        self.log_to_file_checkbox.setStyleSheet(CHECKBOX_STYLE)
        settings_layout.addWidget(self.log_to_file_checkbox)
        
        self.log_to_console_checkbox = QCheckBox("Выводить в консоль")
        self.log_to_console_checkbox.setStyleSheet(CHECKBOX_STYLE)
        settings_layout.addWidget(self.log_to_console_checkbox)
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        # --- Фильтр логов ---
        filter_layout = QHBoxLayout()
        
        filter_label = QLabel("Фильтр по уровню:")
        filter_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        filter_layout.addWidget(filter_label)
        
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["Все", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_filter_combo.setCurrentText("Все")
        self.log_filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_TERTIARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 100px;
            }}
        """)
        self.log_filter_combo.currentTextChanged.connect(self._refresh_app_logs)
        filter_layout.addWidget(self.log_filter_combo)

        filter_layout.addStretch()
        
        self.log_autoscroll_checkbox = QCheckBox("Автопрокрутка")
        self.log_autoscroll_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.log_autoscroll_checkbox.setChecked(True)
        filter_layout.addWidget(self.log_autoscroll_checkbox)
        
        layout.addLayout(filter_layout)

        # --- Поле логов ---
        self.app_log_view = QTextEdit()
        self.app_log_view.setReadOnly(True)
        self.app_log_view.setStyleSheet(LOG_TEXT_STYLE + SCROLLBAR_STYLE)
        self.app_log_view.setMinimumHeight(250)
        self.app_log_view.setPlaceholderText(
            "Здесь отображаются логи приложения (app.log).\n"
            "Нажмите 'Обновить' для загрузки.\n\n"
            "Доступные уровни:\n"
            "  DEBUG    — отладочная информация (серый)\n"
            "  INFO     — основные события (белый)\n"
            "  WARNING  — предупреждения (жёлтый)\n"
            "  ERROR    — ошибки (красный)\n"
            "  CRITICAL — критические ошибки (ярко-красный)"
        )
        layout.addWidget(self.app_log_view, stretch=1)
        
        # --- Кнопки управления (ПОД логом) ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # Обновить
        self.log_refresh_btn = QPushButton("Обновить")
        self.log_refresh_btn.setIcon(qta.icon('mdi.refresh', color='#000000', scale_factor=0.8))
        self.log_refresh_btn.setIconSize(QSize(18, 18))
        self.log_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
        """)
        self.log_refresh_btn.clicked.connect(self._refresh_app_logs)
        btn_layout.addWidget(self.log_refresh_btn)

        # Очистить
        self.log_clear_btn = QPushButton("Очистить")
        self.log_clear_btn.setIcon(qta.icon('mdi.delete-empty', color='#000000', scale_factor=0.8))
        self.log_clear_btn.setIconSize(QSize(18, 18))
        self.log_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
        """)
        self.log_clear_btn.clicked.connect(self._clear_app_logs)
        btn_layout.addWidget(self.log_clear_btn)
        
        # Сохранить
        self.log_save_btn = QPushButton("Сохранить")
        self.log_save_btn.setIcon(qta.icon('fa5.save', color='#000000', scale_factor=0.8))
        self.log_save_btn.setIconSize(QSize(18, 18))
        self.log_save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: {COLOR_BG_PRIMARY};
                font-size: 11px;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                spacing: 8px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_ACCENT_PRESSED};
            }}
        """)
        self.log_save_btn.clicked.connect(self._save_app_logs)
        btn_layout.addWidget(self.log_save_btn)
        
        layout.addLayout(btn_layout)
        
        # --- Статус строка ---
        self.log_status_label = QLabel("Лог-файл: app.log | Строк: 0")
        self.log_status_label.setStyleSheet(f"color: {COLOR_TEXT_TERTIARY}; font-size: 10px;")
        layout.addWidget(self.log_status_label)

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

    def _on_db_mode_changed(self, state):
        """Обработка переключения режима БД."""
        enabled = state == Qt.CheckState.Checked
        
        # Активируем/деактивируем поля БД
        self.db_host_input.setEnabled(enabled)
        self.db_port_input.setEnabled(enabled)
        self.db_user_input.setEnabled(enabled)
        self.db_name_input.setEnabled(enabled)
        self.db_retries_input.setEnabled(enabled)
        self.db_retry_delay_input.setEnabled(enabled)
        
        if enabled:
            self.db_status_label.setText("Будет выполнена попытка подключения при применении")
            self.db_status_label.setStyleSheet("color: #FFD600; font-size: 10px;")
        else:
            self.db_status_label.setText("Файловый режим (без БД)")
            self.db_status_label.setStyleSheet("color: #888888; font-size: 10px;")

    def _start_scan(self):
        """Запустить сканирование хранилища."""
        path = self.storage_path_input.text().strip()
        if not path:
            self._append_log("Ошибка: путь к хранилищу не задан", "ERROR")
            return
        
        root_path = Path(path)
        if not root_path.exists():
            self._append_log(f"Ошибка: каталог не существует: {path}", "ERROR")
            return
        
        # Очищаем лог
        self.scan_log.clear()
        self.save_log_btn.setEnabled(False)
        
        # UI в режим сканирования
        self.scan_btn.setEnabled(False)
        self.scan_cancel_btn.setEnabled(True)
        self.add_to_list_btn.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_progress.setRange(0, 0)  # Бесконечный
        
        # Запускаем worker
        self._scan_worker = ScanWorker(root_path, self)
        self._scan_worker.log_message.connect(self._append_log_html)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished_scan.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.archive_found.connect(self._on_archive_found)
        self._found_archives: list = []  # Собираем найденные архивы
        self._scan_worker.start()

    def _cancel_scan(self):
        """Отменить сканирование."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._append_log("Отмена сканирования...", "WARNING")

    def _on_archive_found(self, candidate):
        """Сохранить найденный архив для передачи в таблицу."""
        # Форматируем дату
        date_str = "—"
        if candidate.record_date:
            try:
                d = candidate.record_date
                date_str = f"{d[6:8]}.{d[4:6]}.{d[0:4]}"
            except Exception:
                date_str = candidate.record_date
        
        archive = {
            'turbine': candidate.wtg_id or "Unknown",
            'date_str': date_str,
            'size': f"{candidate.file_size_kb:.0f} КБ",
            'path': str(candidate.path),
            'filename': candidate.filename
        }
        self._found_archives.append(archive)

    def _on_scan_progress(self, current: int, total: int):
        """Обновить прогресс сканирования."""
        if total > 0:
            self.scan_progress.setRange(0, total)
            self.scan_progress.setValue(current)
        else:
            self.scan_progress.setRange(0, 0)

    def _on_scan_finished(self, total: int, processed: int, errors: int):
        """Обработка завершения сканирования."""
        self.scan_btn.setEnabled(True)
        self.scan_cancel_btn.setEnabled(False)
        self.scan_progress.setVisible(False)
        self.save_log_btn.setEnabled(True)
        
        self._append_log(
            f"Сканирование завершено. Всего: {total}, обработано: {processed}, ошибок: {errors}",
            "SUCCESS"
        )

        # Активируем кнопку "Добавить в список" если есть найденные архивы
        if self._found_archives:
            self._append_log(f"Найдено архивов: {len(self._found_archives)}. Нажмите 'Добавить в список' для загрузки.", "SUCCESS")
            self.add_to_list_btn.setEnabled(True)

    def _add_to_list(self):
        """Добавить найденные архивы в список и перейти на Home."""
        if self._found_archives:
            self._append_log(f"Добавлено в список: {len(self._found_archives)} архивов", "SUCCESS")
            self.archives_found.emit(self._found_archives)
            self._found_archives = []

        self.add_to_list_btn.setEnabled(False)
        self.switch_to_home.emit()
        self.accept()

    def _on_scan_error(self, error_msg: str):
        """Обработка ошибки сканирования."""
        self._append_log(error_msg, "ERROR")

    def _append_log(self, message: str, level: str = "INFO"):
        """Добавить сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "#BBBBBB",
            "SUCCESS": "#00C853",
            "WARNING": "#FFD600",
            "ERROR": "#DD2C00"
        }
        color = colors.get(level, "#BBBBBB")
        html = f'<span style="color:#666666;">[{timestamp}]</span> <span style="color:{color};">{message}</span><br>'
        self.scan_log.append(html)
        # Автопрокрутка
        scrollbar = self.scan_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_log_html(self, html: str):
        """Добавить HTML в лог."""
        self.scan_log.append(html)
        scrollbar = self.scan_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _save_scan_log(self):
        """Сохранить лог сканирования в файл."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить лог", "scan_log.txt", "Текстовые файлы (*.txt)"
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.scan_log.toPlainText())
                self._append_log(f"Лог сохранён: {path}", "SUCCESS")
            except Exception as e:
                self._append_log(f"Ошибка сохранения лога: {e}", "ERROR")

    def _browse_storage_path(self):
        """Выбрать путь к хранилищу."""
        path = QFileDialog.getExistingDirectory(
            self, "Выберите папку с архивами",
            self.storage_path_input.text() or ""
        )
        if path:
            self.storage_path_input.setText(path)

    def _get_log_file_path(self) -> Path:
        """Получить путь к файлу логов."""
        return Path(__file__).resolve().parent.parent.parent / "app.log"

    def _refresh_app_logs(self):
        """Обновить отображение логов приложения."""
        log_path = self._get_log_file_path()
        
        if not log_path.exists():
            self.app_log_view.setHtml(
                '<span style="color:#888888;">Лог-файл app.log ещё не создан. '
                'Запустите какие-либо операции для генерации логов.</span>'
            )
            self.log_status_label.setText("Лог-файл: app.log | Не найден")
            return
        
        try:
            # Читаем последние 500 строк
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Ограничиваем размер (последние 500 строк)
            if len(lines) > 500:
                lines = lines[-500:]
            
            filter_level = self.log_filter_combo.currentText()
            
            # Форматируем с цветами
            formatted_lines = []
            visible_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Определяем уровень из строки лога
                level = "INFO"
                if " - DEBUG - " in line:
                    level = "DEBUG"
                elif " - INFO - " in line:
                    level = "INFO"
                elif " - WARNING - " in line:
                    level = "WARNING"
                elif " - ERROR - " in line:
                    level = "ERROR"
                elif " - CRITICAL - " in line:
                    level = "CRITICAL"
                
                # Фильтрация по уровню
                if filter_level != "Все" and level != filter_level:
                    continue
                
                visible_count += 1
                
                # Цвета для уровней
                colors = {
                    "DEBUG": "#888888",
                    "INFO": "#CCCCCC",
                    "WARNING": "#FFD600",
                    "ERROR": "#FF6D00",
                    "CRITICAL": "#DD2C00"
                }
                color = colors.get(level, "#CCCCCC")
                
                # Форматируем строку
                parts = line.split(" - ", 3)
                if len(parts) >= 4:
                    timestamp, module, lvl, message = parts
                    html = (
                        f'<span style="color:#555555;">{timestamp}</span> | '
                        f'<span style="color:#448AFF;">{module}</span> | '
                        f'<span style="color:{color}; font-weight:bold;">{lvl}</span> | '
                        f'<span style="color:{color};">{message}</span><br>'
                    )
                else:
                    html = f'<span style="color:{color};">{line}</span><br>'
                
                formatted_lines.append(html)
            
            if formatted_lines:
                self.app_log_view.setHtml(''.join(formatted_lines))
                self.log_status_label.setText(f"Лог-файл: app.log | Строк: {visible_count} (из {len(lines)})")
            else:
                self.app_log_view.setHtml(
                    f'<span style="color:#888888;">Нет логов уровня {filter_level}. '
                    f'Выберите другой фильтр или измените уровень логирования в настройках.</span>'
                )
                self.log_status_label.setText(f"Лог-файл: app.log | Строк: 0")
            
            # Автопрокрутка
            if self.log_autoscroll_checkbox.isChecked():
                scrollbar = self.app_log_view.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            self.app_log_view.setHtml(
                f'<span style="color:#DD2C00;">Ошибка чтения лога: {e}</span>'
            )
            self.log_status_label.setText("Ошибка чтения лога")

    def _clear_app_logs(self):
        """Очистить отображение логов."""
        self.app_log_view.clear()
        self.log_status_label.setText("Лог очищен (отображение)")

    def _save_app_logs(self):
        """Сохранить логи в файл."""
        log_path = self._get_log_file_path()
        
        if not log_path.exists():
            self._append_log("Лог-файл не найден", "ERROR")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить логи", "application_logs.txt", "Текстовые файлы (*.txt)"
        )
        if save_path:
            try:
                # Копируем содержимое
                with open(log_path, 'r', encoding='utf-8', errors='replace') as src:
                    content = src.read()
                
                with open(save_path, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                
                self._append_log(f"Логи сохранены: {save_path}", "SUCCESS")
                show_info(self, "Логи сохранены", f"Файл:\n{save_path}")
                
            except Exception as e:
                self._append_log(f"Ошибка сохранения логов: {e}", "ERROR")
                show_critical(self, "Ошибка", f"Не удалось сохранить логи:\n{e}")

    def _check_modules(self):
        """Проверить статус критических модулей."""
        # Очищаем старые индикаторы
        while self.modules_layout.count():
            item = self.modules_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

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
                return bool(self.repository_switcher and self.repository_switcher.mode == 'postgres')
            elif name == "asyncpg":
                import asyncpg  # type: ignore[import-untyped]
                return True
            elif name == "SQLAlchemy":
                import sqlalchemy  # type: ignore[import-untyped]
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

    def _load_settings(self):
        """Загрузить текущие настройки."""
        # База данных
        self.db_host_input.setText(settings.db_host)
        self.db_port_input.setValue(settings.db_port)
        self.db_user_input.setText(settings.db_user)
        self.db_name_input.setText(settings.db_name)
        self.db_retries_input.setValue(int(settings.db_connect_retries))
        self.db_retry_delay_input.setValue(int(settings.db_connect_retry_delay))
        self.db_enabled_checkbox.setChecked(settings.use_database)
        
        # Обновляем статус
        self._on_db_mode_changed(Qt.CheckState.Checked if settings.use_database else Qt.CheckState.Unchecked)

        # Хранилище
        self.storage_path_input.setText(str(settings.archive_storage_path))

        # Логирование
        log_level = getattr(settings, 'log_level', 'INFO')
        index = self.log_level_combo.findText(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        
        self.log_to_file_checkbox.setChecked(True)
        self.log_to_console_checkbox.setChecked(True)

        # Загружаем логи приложения
        self._refresh_app_logs()

    def _apply_settings(self):
        """Применить настройки (без перезапуска)."""
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
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                updated_lines = []
                for line in lines:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in new_settings:
                            value = new_settings[key]
                            updated_lines.append(f"{key}={value}\n")
                            continue
                    updated_lines.append(line)

                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(updated_lines)

            # Перезагружаем настройки
            from ..dal.config import Settings
            settings.__init__()

            # Динамически переключаем репозиторий
            if self.repository_switcher:
                self.repository_switcher.switch_mode(settings.use_database)

            # Сигнализируем об изменении
            self.settings_changed.emit()

            self.accept()

        except Exception as e:
            from .styled_message_box import show_critical
            show_critical(self, "Ошибка применения", 
                         f"Не удалось применить настройки:\n{str(e)}")


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
