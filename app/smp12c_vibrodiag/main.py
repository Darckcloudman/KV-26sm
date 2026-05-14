"""Точка входа в приложение SMP12C VibroDiag Analyzer"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def main():
    """Основная функция запуска"""
    # Включение HiDPI
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Создание приложения
    app = QApplication(sys.argv)
    app.setApplicationName('SMP12C VibroDiag Analyzer')
    app.setOrganizationName('SMP12C')
    
    # Применение тёмной темы
    from smp12c_vibrodiag.gui.styles import STYLESHEET
    app.setStyleSheet(STYLESHEET)
    
    # Импортируем MainWindow после настройки QApplication
    from smp12c_vibrodiag.gui.main_window import MainWindow
    
    # Создание главного окна
    window = MainWindow()
    window.show()
    
    # Запуск цикла событий
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
