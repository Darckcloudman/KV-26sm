"""Точка входа в приложение SMP12C VibroDiag Analyzer v1.2"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


def main():
    """Основная функция запуска."""
    # PySide6 автоматически поддерживает HiDPI
    
    # Создание приложения
    app = QApplication(sys.argv)
    app.setApplicationName('SMP12C VibroDiag Analyzer')
    app.setApplicationVersion('1.2')
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
