"""Точка входа в приложение SMP12C VibroDiag Analyzer v1.3

С поддержкой DAL (Data Access Layer) и PostgreSQL.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from smp12c_vibrodiag.dal.logger import setup_logging
from smp12c_vibrodiag.dal.config import settings


def main():
    """Основная функция запуска."""
    # Настройка логирования DAL
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    setup_logging(level=log_level)
    
    # PySide6 автоматически поддерживает HiDPI
    
    # Создание приложения
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Принудительно используем Fusion стиль для консистентности
    app.setApplicationName('SMP12C VibroDiag Analyzer')
    app.setApplicationVersion('1.3')
    app.setOrganizationName('SMP12C')
    
    # Применение стилей (закомментировано для отладки)
    # from smp12c_vibrodiag.gui.styles import STYLESHEET
    # app.setStyleSheet(STYLESHEET)
    
    # Импортируем MainWindow после настройки QApplication
    from smp12c_vibrodiag.gui.main_window import MainWindow
    
    # Создание главного окна
    window = MainWindow()
    window.show()
    
    # Запуск цикла событий
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
