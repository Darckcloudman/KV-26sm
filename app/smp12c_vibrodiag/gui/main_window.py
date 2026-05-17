"""
Главное окно приложения SMP12C VibroDiag Analyzer v1.2

Тёмная тема, PySide6, анализ данных ВЭУ.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QMenuBar, QMenu,
    QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QAction

from .analysis_data_screen import AnalysisDataScreen
from .home_screen import HomeScreen
# from .styles import STYLESHEET  # Убрал для чёрно-белой темы
from ..parsers.rd2_parser import MultiSensorRD2Parser


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMP12C VibroDiag Analyzer v1.2")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        self.current_file = None
        self.parser = None

        self.setup_ui()
        self.setup_menu()
        self.apply_styles()

    def setup_ui(self):
        """Настроить интерфейс."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка Home
        self.home_screen = HomeScreen()
        self.home_screen.analyze_requested.connect(self._on_analyze_requested)
        self.tabs.addTab(self.home_screen, "Home")

        # Вкладка Анализ данных
        self.analysis_screen = AnalysisDataScreen()
        self.tabs.addTab(self.analysis_screen, "Анализ данных")

        self.statusBar().showMessage("Готов к работе")

    def _on_analyze_requested(self, parser):
        """Обработать запрос анализа из HomeScreen."""
        self.parser = parser
        self.current_file = self.home_screen.current_file
        self.analysis_screen.set_parser(parser)
        self.tabs.setCurrentWidget(self.analysis_screen)
        available = parser.get_available_sensors()
        self.statusBar().showMessage(
            f"Готово: {Path(self.current_file).name} | Датчики: {available}"
        )

    def setup_menu(self):
        """Настроить меню."""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        open_action = QAction("Открыть архив...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_archive)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        """Показать диалог «О программе»."""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>SMP12C VibroDiag Analyzer</h2>"
            "<p><b>Версия:</b> 1.2</p>"
            "<p>Система анализа вибрационной диагностики ветротурбин</p>"
            "<p><b>Разработано:</b> A.Telezhenko, 2026</p>"
            "<p><b>Стандарты:</b> ISO 10816-21:2015, ГОСТ 10816-21-2021</p>"
        )

    def apply_styles(self):
        """Применить стили (закомментировано для чёрно-белой темы Home)."""
        # self.setStyleSheet(STYLESHEET)

    def load_archive(self):
        """Загрузить архив с данными (через меню Файл)."""
        self.home_screen._load_archive()

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите закрыть приложение?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
