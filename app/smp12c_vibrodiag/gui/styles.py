"""CSS стили для PyQt5 виджетов - Чёрный фон с белыми кнопками (Arial)"""

STYLESHEET = """
QMainWindow {
    background-color: #000000;
}

QWidget {
    background-color: #000000;
    color: #e0e0e0;
    font-family: 'Arial', sans-serif;
}

QPushButton {
    background-color: transparent;
    color: #ffffff;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 8px 16px;
    font-family: 'Arial', sans-serif;
    font-size: 13px;
    font-weight: 500;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #ffffff;
    box-shadow: 0 0 0 1px #ffffff;
}

QPushButton:pressed {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #e0e0e0;
}

QPushButton:disabled {
    background-color: transparent;
    color: #444444;
    border: 1px solid #333333;
}

QTabWidget::pane {
    border: 1px solid #333333;
    border-radius: 4px;
    background-color: #000000;
}

QTabBar::tab {
    background-color: #111111;
    color: #888888;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #333333;
    border-bottom: none;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #000000;
    border-bottom: 2px solid #ffffff;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #222222;
    color: #ffffff;
}

QStatusBar {
    background-color: #000000;
    color: #666666;
    border-top: 1px solid #333333;
    font-size: 11px;
}

QMenu {
    background-color: #111111;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 5px;
}

QMenu::item {
    padding: 8px 25px;
    color: #e0e0e0;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #333333;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background: #333333;
    margin: 5px 0;
}

QScrollArea {
    border: 1px solid #333333;
    background-color: #000000;
}

QLabel {
    color: #e0e0e0;
    font-size: 12px;
    font-family: 'Arial', sans-serif;
}

QMessageBox {
    background-color: #111111;
}

QMessageBox QLabel {
    color: #e0e0e0;
}

QFileDialog {
    background-color: #111111;
}

QLineEdit {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: 'Arial', sans-serif;
    font-size: 12px;
}

QLineEdit:focus {
    border: 1px solid #ffffff;
}

QScrollBar:vertical {
    background-color: #0a0a0a;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #ffffff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0a0a0a;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #333333;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #ffffff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

