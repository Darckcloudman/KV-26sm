"""Кастомный виджет MetricCard с круговым прогресс-баром."""

from typing import Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPaintEvent, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget


class CircularProgressBar(QFrame):
    """Круговой прогресс-бар."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        min_value: float = 0.0,
        max_value: float = 100.0,
        color: str = "#00C853"
    ):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.color = QColor(color)
        self.setFixedSize(80, 80)

    def set_value(self, value: float) -> None:
        """Установить текущее значение."""
        self.current_value = max(self.min_value, min(value, self.max_value))
        self.update()

    def set_color(self, color: str) -> None:
        """Установить цвет прогресс-бара."""
        self.color = QColor(color)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Центрируем
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 8

        # Рисуем фоновую дугу (серый)
        painter.setPen(QPen(QColor("#444444"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(
            int(center.x() - radius), int(center.y() - radius),
            int(radius * 2), int(radius * 2),
            90 * 16, -270 * 16
        )

        # Рисуем прогресс
        progress_percent = (self.current_value - self.min_value) / (self.max_value - self.min_value) if self.max_value != self.min_value else 0
        sweep_angle = int(270 * progress_percent)

        painter.setPen(QPen(self.color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(
            int(center.x() - radius), int(center.y() - radius),
            int(radius * 2), int(radius * 2),
            90 * 16, -sweep_angle
        )

        # Центральное значение
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{progress_percent:.0f}%"
        )


class MetricCard(QFrame):
    """Виджет карточки метрики с заголовком, значением и круговым прогресс-баром."""

    def __init__(
        self,
        title: str,
        value: float,
        unit: str,
        max_value: Optional[float] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.unit = unit
        self.max_value = max_value
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            MetricCard {
                background-color: #2D2D2D;
                border: 1px solid #444444;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Заголовок
        self.title_label = QLabel(self.title, self)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                font-weight: Normal;
            }
        """)
        layout.addWidget(self.title_label)

        # Значение и единица
        value_layout = QVBoxLayout()
        value_layout.setSpacing(4)

        self.value_label = QLabel(self)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: Bold;
            }
        """)
        self.update_value_display()
        value_layout.addWidget(self.value_label)

        self.unit_label = QLabel(self.unit, self)
        self.unit_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
            }
        """)
        value_layout.addWidget(self.unit_label)

        layout.addLayout(value_layout)

        # Прогресс-бар (если задан max_value)
        self.progress_bar = None
        if self.max_value is not None:
            self.progress_bar = CircularProgressBar(self, max_value=self.max_value)
            self.update_progress()
            layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addStretch()

    def update_value_display(self) -> None:
        """Обновить отображение значения."""
        try:
            val = float(self.value)
        except (ValueError, TypeError):
            val = 0.0
        if self.max_value is not None:
            self.value_label.setText(f"{val:.2f}")
        else:
            self.value_label.setText(f"{val:.3f}")

    def update_progress(self) -> None:
        """Обновить прогресс-бар."""
        if self.max_value is not None and self.progress_bar:
            percentage = (self.value / self.max_value) * 100
            self.progress_bar.set_value(percentage)

            # Установить цвет в зависимости от процента
            if percentage < 70:
                self.progress_bar.set_color("#00C853")  # Зелёный
            elif percentage < 90:
                self.progress_bar.set_color("#FFD600")  # Жёлтый
            else:
                self.progress_bar.set_color("#D50000")  # Красный

    def set_value(self, value: float) -> None:
        """Установить новое значение."""
        self.value = value
        self.update_value_display()
        self.update_progress()
