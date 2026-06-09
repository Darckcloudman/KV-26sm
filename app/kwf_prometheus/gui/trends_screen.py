# -*- coding: utf-8 -*-
"""
Вкладка "Тренды" v1.4 — график изменения уровня вибрации (RMS) по времени.

Поддерживает:
- Выбор конкретной ВЭУ из списка
- Отображение среднего по ветропарку
- Загрузку данных из PostgreSQL (асинхронно)
- Файловый режим (с уведомлением)
"""

import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread
import pyqtgraph as pg

from ..dal.repositories.base import IVibrationRepository
from ..dal.config import settings
from ..dal.logger import get_logger
from .ui_styles import CHECKBOX_STYLE
from .workers.trends_worker import TrendsWorker
from .styled_message_box import show_critical, show_info
from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY, COLOR_ACCENT,
    COLOR_BORDER, BUTTON_STYLE
)

logger = get_logger("TrendsScreen")


class TurbinesLoaderThread(QThread):
    """Поток для загрузки списка турбин."""

    turbines_ready = Signal(object)  # List[Dict]
    error = Signal(str)

    def __init__(self, repository: IVibrationRepository, parent=None):
        super().__init__(parent)
        self.repository = repository

    def run(self):
        import asyncio
        try:
            turbines = asyncio.run(self.repository.list_turbines())
            self.turbines_ready.emit(turbines)
        except Exception as e:
            logger.error("Ошибка загрузки турбин: %s", e, exc_info=True)
            self.error.emit(str(e))


class TrendsScreen(QWidget):
    """Вкладка для анализа трендов вибрации."""

    def __init__(self, repository: Optional[IVibrationRepository] = None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._turbines: List[Dict[str, Any]] = []
        self._trends_worker: Optional[TrendsWorker] = None
        self._turbines_loader: Optional[TurbinesLoaderThread] = None

        self.setStyleSheet(f"background-color: {COLOR_BG_PRIMARY};")
        self._setup_ui()
        self._load_turbines()

    def _setup_ui(self):
        """Настроить интерфейс."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === Заголовок ===
        title = QLabel("Тренды RMS по времени")
        title.setStyleSheet(f"""
            color: {COLOR_TEXT_PRIMARY};
            font-size: 18px;
            font-weight: bold;
            padding: 10px;
            border-bottom: 2px solid {COLOR_BORDER};
        """)
        main_layout.addWidget(title)

        # === Предупреждение для файлового режима ===
        self.file_mode_warning = QLabel(
            "Для отображения трендов требуется подключение к PostgreSQL.\n"
            "Переключитесь в режим БД через Настройки."
        )
        self.file_mode_warning.setStyleSheet(f"""
            color: {COLOR_TEXT_TERTIARY};
            font-size: 12px;
            padding: 15px;
            background-color: {COLOR_BG_SECONDARY};
            border: 1px solid {COLOR_BORDER};
            border-radius: 5px;
        """)
        self.file_mode_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_mode_warning.setVisible(not settings.use_database)
        main_layout.addWidget(self.file_mode_warning)

        # === Панель управления ===
        control_panel = QFrame()
        control_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setSpacing(12)

        # Выбор турбины
        turbine_label = QLabel("ВЭУ:")
        turbine_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        control_layout.addWidget(turbine_label)

        self.turbine_combo = QComboBox()
        self.turbine_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }}
        """)
        self.turbine_combo.setEnabled(False)
        control_layout.addWidget(self.turbine_combo)

        # Среднее по ветропарку
        self.avg_park_checkbox = QCheckBox("Среднее по ветропарку")
        self.avg_park_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.avg_park_checkbox.stateChanged.connect(self._on_avg_park_changed)
        control_layout.addWidget(self.avg_park_checkbox)

        control_layout.addSpacing(20)

        # Выбор датчика
        sensor_label = QLabel("Датчик:")
        sensor_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        control_layout.addWidget(sensor_label)

        self.sensor_combo = QComboBox()
        self.sensor_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 80px;
            }}
        """)
        for sid in range(1, 9):
            self.sensor_combo.addItem(f"Датчик {sid}", sid)
        control_layout.addWidget(self.sensor_combo)

        # Выбор типа фильтра
        filter_label = QLabel("Фильтр:")
        filter_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px;")
        control_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("НЧ (0.1-10 Гц)", "FILTER")
        self.filter_combo.addItem("ВЧ (10-1000 Гц)", "LOW")
        self.filter_combo.addItem("ВЧ(ф) (0-12 кГц)", "HIGH")
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_BG_PRIMARY};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 140px;
            }}
        """)
        control_layout.addWidget(self.filter_combo)

        control_layout.addStretch()

        # Кнопка "Построить"
        self.build_btn = QPushButton("Построить")
        self.build_btn.setStyleSheet(BUTTON_STYLE)
        self.build_btn.setFixedWidth(120)
        self.build_btn.clicked.connect(self._build_trend)
        control_layout.addWidget(self.build_btn)

        main_layout.addWidget(control_panel)

        # === Прогресс-бар ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLOR_BG_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 3px;
                text-align: center;
                color: {COLOR_TEXT_TERTIARY};
                font-size: 9px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 2px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)

        # === График ===
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', COLOR_BG_PRIMARY)
        pg.setConfigOption('foreground', COLOR_TEXT_PRIMARY)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("RMS по времени", color=COLOR_TEXT_PRIMARY, size="12px")
        self.plot_widget.setLabel('bottom', 'Дата записи', color=COLOR_TEXT_SECONDARY)
        self.plot_widget.setLabel('left', 'RMS (мм/с)', color=COLOR_TEXT_SECONDARY)

        # Сетка
        self.plot_widget.getAxis('bottom').setGrid(128)
        self.plot_widget.getAxis('left').setGrid(128)
        self.plot_widget.getAxis('bottom').setTextPen(COLOR_TEXT_TERTIARY)
        self.plot_widget.getAxis('left').setTextPen(COLOR_TEXT_TERTIARY)

        # Кривая тренда
        self.plot_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=COLOR_ACCENT, width=2, style=Qt.PenStyle.SolidLine),
            symbol='o',
            symbolBrush=COLOR_ACCENT,
            symbolPen=COLOR_ACCENT,
            symbolSize=6
        )

        # Пороговые линии зон (скрыты по умолчанию)
        self.threshold_lines = []
        zone_colors = {'A': '#00C853', 'B': '#FFC107', 'C': '#FF9800', 'D': '#DD2C00'}
        zone_values = {'A': 2.3, 'B': 4.5, 'C': 7.8}
        for zone, value in zone_values.items():
            line = pg.InfiniteLine(
                pos=value,
                angle=0,
                pen=pg.mkPen(color=zone_colors[zone], width=1, style=Qt.PenStyle.DashLine)
            )
            line.setVisible(False)
            self.plot_widget.addItem(line)
            self.threshold_lines.append((zone, line))

        main_layout.addWidget(self.plot_widget, 1)

        # === Статистика ===
        stats_panel = QFrame()
        stats_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setSpacing(20)

        self.stat_labels = {}
        for key, title in [('min', 'Мин'), ('max', 'Макс'), ('avg', 'Среднее'), ('count', 'Точек')]:
            label = QLabel(f"{title}: —")
            label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            stats_layout.addWidget(label)
            self.stat_labels[key] = label

        stats_layout.addStretch()
        main_layout.addWidget(stats_panel)

    def _load_turbines(self):
        """Загрузить список турбин из репозитория."""
        if not settings.use_database or self.repository is None:
            return

        self.turbine_combo.clear()
        self.turbine_combo.addItem("Загрузка...", None)
        self.turbine_combo.setEnabled(False)

        # Запускаем поток загрузки
        self._turbines_loader = TurbinesLoaderThread(self.repository, self)
        self._turbines_loader.turbines_ready.connect(self._on_turbines_loaded)
        self._turbines_loader.error.connect(self._on_turbines_error)
        self._turbines_loader.start()

    def _on_turbines_loaded(self, turbines: List[Dict[str, Any]]):
        """Обработка загрузки списка турбин."""
        self._turbines = turbines
        self.turbine_combo.clear()

        if not turbines:
            self.turbine_combo.addItem("Нет данных", None)
            self.turbine_combo.setEnabled(False)
            return

        for turbine in turbines:
            wtg_id = turbine.get('wtg_id', 'Unknown')
            total = turbine.get('total_archives', 0)
            self.turbine_combo.addItem(f"{wtg_id} ({total} записей)", wtg_id)

        self.turbine_combo.setEnabled(True)

    def _on_turbines_error(self, error_msg: str):
        """Обработка ошибки загрузки турбин."""
        logger.error("Ошибка загрузки турбин: %s", error_msg)
        self.turbine_combo.clear()
        self.turbine_combo.addItem("Ошибка загрузки", None)

    def _on_avg_park_changed(self, state):
        """При переключении 'Среднее по ветропарку'."""
        self.turbine_combo.setEnabled(state != Qt.CheckState.Checked)

    def _build_trend(self):
        """Построить график трендов."""
        if not settings.use_database or self.repository is None:
            show_info(self, "Информация", "Тренды доступны только в режиме PostgreSQL.")
            return

        # Получаем параметры
        wtg_id = None if self.avg_park_checkbox.isChecked() else self.turbine_combo.currentData()
        sensor_id = self.sensor_combo.currentData()
        filter_type = self.filter_combo.currentData()

        if not self.avg_park_checkbox.isChecked() and wtg_id is None:
            show_critical(self, "Ошибка", "Выберите ВЭУ или включите 'Среднее по ветропарку'")
            return

        # Показываем прогресс
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.build_btn.setEnabled(False)

        # Останавливаем предыдущий воркер
        if self._trends_worker and self._trends_worker.isRunning():
            self._trends_worker.terminate()

        # Запускаем воркер
        self._trends_worker = TrendsWorker(
            self.repository, wtg_id, sensor_id, filter_type, self
        )
        self._trends_worker.trend_ready.connect(self._on_trend_loaded)
        self._trends_worker.error.connect(self._on_trend_error)
        self._trends_worker.start()

    def _on_trend_loaded(self, trend_data: List[Dict[str, Any]]):
        """Обработка загрузки тренда."""
        self.progress_bar.setVisible(False)
        self.build_btn.setEnabled(True)

        if not trend_data:
            show_info(self, "Нет данных", "Не найдено данных для построения тренда.")
            self.plot_curve.clear()
            self._clear_stats()
            return

        # Сортируем по дате
        trend_data.sort(key=lambda x: x.get('date') or '')

        # Извлекаем даты и значения
        dates = []
        values = []
        for point in trend_data:
            date_str = point.get('date')
            rms = point.get('rms_total')
            if date_str and rms is not None:
                try:
                    dt = datetime.fromisoformat(date_str)
                    dates.append(dt)
                    values.append(rms)
                except (ValueError, TypeError):
                    continue

        if not dates or not values:
            show_info(self, "Нет данных", "Не удалось распарсить даты.")
            self.plot_curve.clear()
            self._clear_stats()
            return

        # Строим график (X — timestamp, Y — RMS)
        x_values = [dt.timestamp() for dt in dates]
        self.plot_curve.setData(x_values, values)

        # Форматируем ось X
        self.plot_widget.getAxis('bottom').setTicks([
            [(t, dt.strftime("%d.%m")) for t, dt in zip(x_values, dates)]
        ])

        # Показываем пороговые линии
        for zone, line in self.threshold_lines:
            line.setVisible(True)

        # Обновляем статистику
        self._update_stats(values)

        logger.info("Тренд построен: %d точек", len(values))

    def _on_trend_error(self, error_msg: str):
        """Обработка ошибки загрузки тренда."""
        self.progress_bar.setVisible(False)
        self.build_btn.setEnabled(True)
        logger.error("Ошибка построения тренда: %s", error_msg)
        show_critical(self, "Ошибка", f"Не удалось построить график:\n{error_msg}")

    def _update_stats(self, values: List[float]):
        """Обновить статистику."""
        if not values:
            self._clear_stats()
            return

        self.stat_labels['min'].setText(f"Мин: {min(values):.4f}")
        self.stat_labels['max'].setText(f"Макс: {max(values):.4f}")
        self.stat_labels['avg'].setText(f"Среднее: {np.mean(values):.4f}")
        self.stat_labels['count'].setText(f"Точек: {len(values)}")

    def _clear_stats(self):
        """Очистить статистику."""
        for key in self.stat_labels:
            self.stat_labels[key].setText(f"{self.stat_labels[key].text().split(':')[0]}: —")

    def refresh(self):
        """Обновить экран (перезагрузить список турбин)."""
        self.file_mode_warning.setVisible(not settings.use_database)
        if settings.use_database:
            self._load_turbines()
