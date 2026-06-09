"""
UI Компонент: Пульсирующая красная точка (PulseRedDot)

Единый шаблон для отображения пульсирующих маркеров пиков:
- Home экран (точки подключения датчиков на shema.png)
- Графики анализа данных (пики на спектрах)

Дизайн:
- Красная точка (#FF3B3B)
- Пульсация: радиус 2px → 6px (диаметр 4px → 12px)
- Плавное исчезновение (opacity: 1.0 → 0.0)
- Бесконечная анимация (InOutQuad easing)
- Tooltip при наведении (опционально)
"""

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, QVariantAnimation, QPointF, QEasingCurve


class PeakPulseDot(QWidget):
    """Пульсирующая красная точка — универсальный маркер пика.
    
    Анимация растущей и исчезающей точки:
    - Радиус: 2px → 6px (диаметр 4px → 12px)
    - Прозрачность: 100% → 0%
    - Бесконечный цикл
    - Easing: InOutQuad (плавное ускорение/замедление)
    
    Args:
        parent: Родительский виджет
        tooltip: Текст подсказки при наведении (опционально)
        size: Базовый размер точки (по умолчанию 30x30px)
    """
    
    def __init__(self, parent=None, tooltip=None, size=30):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._progress = 0.0
        self._tooltip = tooltip
        
        # Анимация: 0.0 → 1.0 за 1000мс
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(1000)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setLoopCount(-1)  # Бесконечно
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.valueChanged.connect(self._on_value_changed)
        self._animation.start()
    
    def _on_value_changed(self, value):
        """Обновить прогресс анимации."""
        self._progress = float(value)
        self.update()
    
    def set_tooltip(self, tooltip: str):
        """Установить текст подсказки."""
        self._tooltip = tooltip
    
    def paintEvent(self, event):
        """Отрисовка пульсирующей точки."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Радиус: от 2px до 6px
        min_radius = 2.0
        max_radius = 6.0
        current_radius = min_radius + (max_radius - min_radius) * self._progress
        
        # Прозрачность: от 100% до 0%
        opacity = 1.0 - self._progress
        
        # Центр точки
        center = QPointF(self.width() / 2, self.height() / 2)
        
        # Отрисовка
        painter.setOpacity(opacity)
        painter.setBrush(QBrush(QColor(255, 59, 59)))  # Ярко-красный #FF3B3B
        painter.setPen(Qt.PenStyle.NoPen)  # Без обводки
        painter.drawEllipse(center, current_radius, current_radius)
    
    def enterEvent(self, event):
        """Показать tooltip при наведении."""
        if self._tooltip:
            rect = self.rect()
            QToolTip.showText(self.mapToGlobal(rect.center()), self._tooltip, self, rect)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Скрыть tooltip при уходе курсора."""
        QToolTip.hideText()
        super().leaveEvent(event)


# Экспорт для использования в других модулях
__all__ = ['PeakPulseDot']