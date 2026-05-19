"""
Главное окно приложения SMP12C VibroDiag Analyzer v1.3

Тёмная тема, PySide6, анализ данных ВЭУ.
С поддержкой DAL (Data Access Layer) и PostgreSQL.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMenuBar, QMenu,
    QFrame
)
from .styled_message_box import show_about, show_question
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QAction

from .analysis_data_screen import AnalysisDataScreen
from .home_screen import HomeScreen
# from .styles import STYLESHEET  # Убрал для чёрно-белой темы
from ..parsers.rd2_parser import MultiSensorRD2Parser
from ..dal.repositories import get_repository
from ..dal.config import settings


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SMP12C VibroDiag Analyzer v{settings.app_version}")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        self.current_file = None
        self.parser = None

        # Инициализация репозитория (инъекция зависимости)
        self.repository = get_repository(settings)

        self.setup_ui()
        self.setup_menu()
        self.apply_styles()

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

        # Вкладка Home (передаём репозиторий)
        self.home_screen = HomeScreen(repository=self.repository)
        self.home_screen.analyze_requested.connect(self._on_analyze_requested)
        self.tabs.addTab(self.home_screen, "Home")

        # Вкладка Анализ данных
        self.analysis_screen = AnalysisDataScreen()
        self.tabs.addTab(self.analysis_screen, "Анализ данных")

        self.statusBar().showMessage(
            f"Готов к работе | Режим: {'PostgreSQL' if settings.use_database else 'Файловая система'}"
        )

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

    def load_archive(self):
        """Загрузить архив с данными (через меню Файл)."""
        self.home_screen._load_archive()

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
