"""CSS стили для PyQt5 виджетов - Чёрный фон с розовыми неоновыми кнопками"""

STYLESHEET = """
QMainWindow {
    background-color: #000000;
}

QWidget {
    background-color: #000000;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

QPushButton {
    background-color: transparent;
    color: #ff69b4;
    border: 2px solid #ff69b4;
    border-radius: 6px;
    padding: 10px 20px;
    font-family: 'Segoe UI';
    font-size: 12px;
    font-weight: 500;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #ff69b4;
    color: #000000;
    border: 2px solid #ff69b4;
    box-shadow: 0 0 20px rgba(255, 105, 180, 0.6);
}

QPushButton:pressed {
    background-color: #ff1493;
    color: #000000;
    border: 2px solid #ff1493;
}

QPushButton:disabled {
    background-color: transparent;
    color: #444444;
    border: 2px solid #333333;
}

QTabWidget::pane {
    border: 1px solid #222222;
    border-radius: 6px;
    background-color: #0a0a0a;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #888888;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #222222;
    border-bottom: none;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: #000000;
    border-bottom: 2px solid #ff69b4;
    color: #ff69b4;
}

QTabBar::tab:hover:!selected {
    background-color: #222222;
    color: #ff69b4;
}

QStatusBar {
    background-color: #0a0a0a;
    color: #666666;
    border-top: 1px solid #222222;
    font-size: 11px;
}

QMenu {
    background-color: #1a1a1a;
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
    background-color: #ff69b4;
    color: #000000;
}

QMenu::separator {
    height: 1px;
    background: #333333;
    margin: 5px 0;
}

QScrollArea {
    border: 1px solid #222222;
    background-color: #0a0a0a;
}

QLabel {
    color: #e0e0e0;
    font-size: 11px;
}

QMessageBox {
    background-color: #1a1a1a;
}

QMessageBox QLabel {
    color: #e0e0e0;
}

QFileDialog {
    background-color: #1a1a1a;
}

QLineEdit {
    background-color: #222222;
    color: #e0e0e0;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 5px;
}

QLineEdit:focus {
    border: 1px solid #ff69b4;
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
    background-color: #ff69b4;
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
    background-color: #ff69b4;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""
