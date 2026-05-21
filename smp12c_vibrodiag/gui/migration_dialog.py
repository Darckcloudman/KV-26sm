# -*- coding: utf-8 -*-
"""
Диалог прогресса миграции базы данных.

Отображает прогресс выполнения миграций Alembic в отдельном потоке.
"""

import asyncio
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from ..dal.database import DatabaseManager
from ..dal.logger import get_logger

logger = get_logger("MigrationDialog")


class MigrationWorker(QThread):
    """Поток для выполнения миграций без блокировки GUI."""
    
    step_changed = Signal(str, int)  # сообщение, процент
    finished = Signal(bool, str)     # успех, сообщение
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
    
    def run(self):
        """Выполнить миграции."""
        try:
            logger.info("Начало миграции БД")
            self.step_changed.emit("Проверка подключения к PostgreSQL...", 10)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Проверяем подключение
                connected = loop.run_until_complete(
                    self.db_manager.connect_with_retry()
                )
                if not connected:
                    logger.error("Не удалось подключиться к БД для миграции")
                    self.finished.emit(
                        False,
                        "Не удалось соединиться с базой данных. "
                        "Проверьте параметры подключения или работайте в файловом режиме."
                    )
                    return
                
                self.step_changed.emit("Создание таблиц...", 40)
                
                # Создаём таблицы
                loop.run_until_complete(self.db_manager.init_db())
                
                self.step_changed.emit("Проверка структуры БД...", 80)
                
                # Проверяем health check
                healthy = loop.run_until_complete(self.db_manager.health_check())
                if not healthy:
                    self.finished.emit(
                        False,
                        "Ошибка при проверке структуры базы данных."
                    )
                    return
                
                self.step_changed.emit("Готово!", 100)
                logger.info("Миграция БД успешно завершена")
                self.finished.emit(True, "База данных успешно инициализирована.")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Ошибка миграции БД: %s", e, exc_info=True)
            self.finished.emit(
                False,
                f"Ошибка при обновлении базы данных: {str(e)}"
            )


class MigrationDialog(QDialog):
    """
    Модальный диалог прогресса миграции БД.
    
    Отображает прогресс выполнения и сообщения о текущем этапе.
    """
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.worker = None
        
        self.setWindowTitle("Обновление базы данных")
        self.setFixedSize(450, 180)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowCloseButtonHint
        )
        
        self._setup_ui()
        self._start_migration()
    
    def _setup_ui(self):
        """Настроить интерфейс диалога."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A1A;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #2A2A2A;
                text-align: center;
                color: #FFFFFF;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border: none;
                border-radius: 4px;
                padding: 6px 20px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E8E8E8; }
            QPushButton:disabled { background-color: #333333; color: #666666; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Заголовок
        self.title_label = QLabel("Инициализация базы данных...")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        # Описание текущего шага
        self.step_label = QLabel("Подготовка...")
        self.step_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        layout.addWidget(self.step_label)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        # Кнопка (по умолчанию скрыта)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setVisible(False)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)
    
    def _start_migration(self):
        """Запустить миграцию в отдельном потоке."""
        self.worker = MigrationWorker(self.db_manager, self)
        self.worker.step_changed.connect(self._on_step_changed)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_step_changed(self, message: str, percent: int):
        """Обновить прогресс."""
        self.step_label.setText(message)
        self.progress_bar.setValue(percent)
    
    def _on_finished(self, success: bool, message: str):
        """Миграция завершена."""
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            self.title_label.setText("Готово!")
            self.title_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
            self.step_label.setText(message)
            self.step_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.title_label.setText("Ошибка")
            self.title_label.setStyleSheet("color: #F44336; font-size: 12px; font-weight: bold;")
            self.step_label.setText(message)
            self.step_label.setStyleSheet("color: #F44336; font-size: 11px;")
            # Показываем кнопку закрытия при ошибке
            self.ok_btn.setVisible(True)
            self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
        
        # Если успешно — закрываем автоматически через 1.5 сек
        if success:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, self.accept)
        
        logger.info("MigrationDialog: %s", message)
    
    def closeEvent(self, event):
        """Запретить закрытие во время миграции."""
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
