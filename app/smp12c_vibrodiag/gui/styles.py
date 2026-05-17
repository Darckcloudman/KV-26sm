"""
Тёмная тема для SMP12C VibroDiag Analyzer v1.2
Цветовая схема: #1E1E1E (фон), #FFFFFF (текст)
Исключены: розовый, фиолетовый
"""

STYLESHEET = """
QMainWindow {
    background-color: #1E1E1E;
}

/* Фон задаётся локально для каждого экрана */
QWidget {
    color: #FFFFFF;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

QPushButton {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 8px 16px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
    font-weight: 500;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #3D3D3D;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #1E1E1E;
    border-color: #666666;
}

QPushButton:disabled {
    background-color: #252525;
    color: #666666;
    border-color: #333333;
}

QTabWidget::pane {
    border: 1px solid #444444;
    border-radius: 4px;
    background-color: #1E1E1E;
}

QTabBar::tab {
    background-color: #2D2D2D;
    color: #AAAAAA;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid #444444;
    border-bottom: none;
    font-size: 12px;
}

QTabBar::tab:selected {
    background-color: #1E1E1E;
    border-bottom: 2px solid #00C853;
    color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #3D3D3D;
    color: #FFFFFF;
}

QStatusBar {
    background-color: #1E1E1E;
    color: #888888;
    border-top: 1px solid #444444;
    font-size: 11px;
}

QMenu {
    background-color: #252525;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 5px;
}

QMenu::item {
    padding: 8px 25px;
    color: #FFFFFF;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #3D3D3D;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #444444;
    margin: 5px 0;
}

QScrollArea {
    border: 1px solid #444444;
    background-color: #1E1E1E;
}

QLabel {
    color: #FFFFFF;
    font-size: 12px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
}

QMessageBox {
    background-color: #252525;
}

QMessageBox QLabel {
    color: #FFFFFF;
}

QFileDialog {
    background-color: #252525;
}

QLineEdit {
    background-color: #252525;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 12px;
}

QLineEdit:focus {
    border: 1px solid #00C853;
}

QComboBox {
    background-color: #252525;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 30px;
}

QComboBox:hover {
    border-color: #555555;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #FFFFFF;
}

QComboBox QAbstractItemView {
    background-color: #252525;
    color: #FFFFFF;
    border: 1px solid #444444;
    selection-background-color: #3D3D3D;
}

QProgressBar {
    background-color: #252525;
    border: 1px solid #444444;
    border-radius: 4px;
    text-align: center;
    height: 10px;
}

QProgressBar::chunk {
    background-color: #00C853;
    border-radius: 3px;
}

QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #444444;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1E1E1E;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #444444;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #555555;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

MetricCard {
    background-color: #2D2D2D;
    border: 1px solid #444444;
    border-radius: 8px;
}

QGroupBox {
    border: 1px solid #444444;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #AAAAAA;
}
"""

