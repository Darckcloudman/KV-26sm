# -*- coding: utf-8 -*-
"""
Экран анализа данных v1.4 — с индикаторами датчиков, порогами и таблицей гармоник
"""

import numpy as np
from typing import Optional, TYPE_CHECKING
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

if TYPE_CHECKING:
    from ..parsers.rd2_parser import MultiSensorRD2Parser

from .styled_message_box import show_critical, show_info
from .metric_card import MetricCard
from .charts.time_series_chart import TimeSeriesChart
from .charts.spectrum_chart import SpectrumChart, ACC_THRESHOLDS, VEL_THRESHOLDS, ZONE_COLORS
from ..utils.conversions import kw_to_mw, kwh_to_gwh
from ..utils.vibration_analysis import VibrationAnalyzer

from .ui_styles import (
    COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_BG_TERTIARY,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_BORDER, COLOR_ACCENT,
    BUTTON_STYLE, BUTTON_SMALL_STYLE, TABLE_STYLE, SCROLLBAR_STYLE
)


class ZoneIndicator(QFrame):
    """Индикатор зоны ISO 10816."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 80)
        self._base_style = f"""
            ZoneIndicator {{
                background-color: {COLOR_BG_TERTIARY};
                border-radius: 8px;
                border: 2px solid {COLOR_BORDER};
            }}
        """
        self.setStyleSheet(self._base_style)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f'color: {COLOR_TEXT_SECONDARY}; font-size: 10px;')
        self.title_label.setAlignment(Qt.AlignCenter)  # type: ignore[arg-type]

        self.zone_label = QLabel('-')
        self.zone_label.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 24px; font-weight: bold;')
        self.zone_label.setAlignment(Qt.AlignCenter)  # type: ignore[arg-type]

        self.rms_label = QLabel('—')
        self.rms_label.setStyleSheet(f'color: {COLOR_TEXT_TERTIARY}; font-size: 9px;')
        self.rms_label.setAlignment(Qt.AlignCenter)  # type: ignore[arg-type]

        layout.addWidget(self.title_label)
        layout.addWidget(self.zone_label)
        layout.addWidget(self.rms_label)

    def set_zone(self, zone, rms_value=0.0, unit='мм/с'):
        color = ZONE_COLORS.get(zone, COLOR_BORDER)
        self.zone_label.setText(zone)
        self.zone_label.setStyleSheet(f'color: {color}; font-size: 24px; font-weight: bold;')
        self.rms_label.setText(
            f'СКЗ: {rms_value:.3f} {unit}' if zone != '-' else 'Нет данных'
        )
        self.setStyleSheet(f"""
            ZoneIndicator {{
                background-color: {COLOR_BG_TERTIARY};
                border-radius: 8px;
                border: 2px solid {color};
            }}
        """)


class SensorStatusIndicator(QFrame):
    """Индикатор статуса датчика с 3 секциями (НЧ/ВЧ/ВЧ(ф)) и зонами ISO 10816."""

    clicked = Signal(int)

    def __init__(self, sensor_id, parent=None):
        super().__init__(parent)
        self.sensor_id = sensor_id
        self.setFixedSize(80, 90)
        self.setCursor(Qt.PointingHandCursor)  # type: ignore[arg-type]
        self.selected = False

        # Базовый стиль
        self._base_style = f"""
            QFrame {{
                background-color: {COLOR_BG_SECONDARY};
                border: 2px solid {COLOR_BORDER};
                border-radius: 4px;
            }}
        """
        self.setStyleSheet(self._base_style)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Номер датчика
        self.id_label = QLabel(str(sensor_id))
        self.id_label.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 16px; font-weight: bold;')
        self.id_label.setAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
        layout.addWidget(self.id_label)

        # 3 секции для НЧ/ВЧ/ВЧ(ф)
        self.sections = {}
        for section_name, label in [('acc', 'НЧ'), ('vel', 'ВЧ'), ('hf', 'ВЧ(ф)')]:
            sec = QLabel(label)
            sec.setFixedHeight(18)
            sec.setStyleSheet(f"""
                QLabel {{
                    background-color: {COLOR_BG_TERTIARY};
                    color: {COLOR_TEXT_TERTIARY};
                    border-radius: 2px;
                    font-size: 8px;
                }}
            """)
            sec.setAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
            layout.addWidget(sec)
            self.sections[section_name] = sec

    def set_zones(self, acc_zone='-', vel_zone='-', hf_zone='-'):
        """Установить зоны для 3 секций."""
        for section_name, zone in [('acc', acc_zone), ('vel', vel_zone), ('hf', hf_zone)]:
            color = ZONE_COLORS.get(zone, COLOR_BORDER)
            sec = self.sections[section_name]
            sec.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: {'#000000' if zone in ['A', 'B'] else '#FFFFFF'};
                    border-radius: 2px;
                    font-size: 8px;
                    font-weight: bold;
                }}
            """)

    def setSelected(self, selected):
        """Установить состояние выделения."""
        self.selected = selected
        border_color = COLOR_ACCENT if selected else COLOR_BORDER
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_SECONDARY if not selected else COLOR_BG_TERTIARY};
                border: 2px solid {border_color};
                border-radius: 4px;
            }}
        """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.sensor_id)


class AnalysisDataScreen(QWidget):
    """Экран анализа данных v1.4 с индикаторами датчиков и таблицей гармоник."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser: Optional['MultiSensorRD2Parser'] = None
        self._current_sensor = 1
        self._sensor_zones: dict[int, dict[str, str]] = {}  # {sensor_id: {'acc': zone, 'vel': zone, 'hf': zone}}
        self._all_peaks: list[dict] = []  # Данные пиков для таблицы
        self._current_peaks: dict[str, list[dict]] = {}  # Пику по типам сигналов для графиков
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {COLOR_BG_PRIMARY};")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # === Ряд 1: Метрики турбины ===
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(10)

        self.metric_cards = {
            'power': MetricCard('Мощность', 0.0, 'МВт'),
            'rpm': MetricCard('Частота вращения', 0.0, 'об/мин'),
            'wind': MetricCard('Скорость ветра', 0.0, 'м/с'),
            'energy': MetricCard('Накопленная выработка', 0.0, 'ГВт·ч'),
        }
        for card in self.metric_cards.values():
            metrics_layout.addWidget(card, 1)
        main_layout.addLayout(metrics_layout)

        # === Ряд 2: Индикаторы датчиков + Зоны + Экспорт ===
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        # Индикаторы 8 датчиков (слева)
        sensors_title = QLabel('Датчики:')
        sensors_title.setStyleSheet(f'color: {COLOR_TEXT_SECONDARY}; font-size: 11px;')
        controls_layout.addWidget(sensors_title)

        self.sensor_indicators = {}
        sensors_wrapper = QHBoxLayout()
        sensors_wrapper.setSpacing(4)
        for sensor_id in range(1, 9):
            indicator = SensorStatusIndicator(sensor_id, self)
            indicator.clicked.connect(self._on_sensor_indicator_clicked)
            sensors_wrapper.addWidget(indicator)
            self.sensor_indicators[sensor_id] = indicator
        controls_layout.addLayout(sensors_wrapper, 0)

        controls_layout.addStretch(1)

        # Зоны ISO 10816 (центр)
        zones_wrapper = QHBoxLayout()
        zones_wrapper.setSpacing(6)
        zones_title = QLabel('Зоны ISO 10816')
        zones_title.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: bold;')
        zones_wrapper.addWidget(zones_title)

        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(6)
        self.zone_indicators = {
            'acc': ZoneIndicator('НЧ Acc'),
            'vel': ZoneIndicator('ВЧ Vel'),
            'hf': ZoneIndicator('ВЧ(ф)'),
        }
        for zi in self.zone_indicators.values():
            zones_layout.addWidget(zi)
        zones_wrapper.addLayout(zones_layout)
        controls_layout.addLayout(zones_wrapper, 0)

        controls_layout.addStretch(1)

        # Кнопки экспорта (справа)
        export_layout = QHBoxLayout()
        export_layout.setSpacing(4)

        self.export_csv_btn = QPushButton("CSV")
        self.export_csv_btn.setStyleSheet(BUTTON_SMALL_STYLE)
        self.export_csv_btn.setToolTip("Экспорт в CSV")
        self.export_csv_btn.setFixedHeight(28)
        self.export_csv_btn.clicked.connect(self._export_csv)
        export_layout.addWidget(self.export_csv_btn)

        self.export_excel_btn = QPushButton("Excel")
        self.export_excel_btn.setStyleSheet(BUTTON_SMALL_STYLE)
        self.export_excel_btn.setToolTip("Экспорт в Excel")
        self.export_excel_btn.setFixedHeight(28)
        self.export_excel_btn.clicked.connect(self._export_excel)
        export_layout.addWidget(self.export_excel_btn)

        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setStyleSheet(BUTTON_SMALL_STYLE)
        self.export_pdf_btn.setToolTip("Сформировать PDF-отчёт")
        self.export_pdf_btn.setFixedHeight(28)
        self.export_pdf_btn.clicked.connect(self._export_pdf)
        export_layout.addWidget(self.export_pdf_btn)

        controls_layout.addLayout(export_layout)
        main_layout.addLayout(controls_layout)

        # === Ряд 3: Временные ряды ===
        ts_title = QLabel('Временные ряды')
        ts_title.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: bold;')
        main_layout.addWidget(ts_title)

        ts_layout = QHBoxLayout()
        ts_layout.setSpacing(10)
        self.ts_acc_chart = TimeSeriesChart('НЧ (0.1–10 Гц) — Ускорение', 'м/с²')
        self.ts_vel_chart = TimeSeriesChart('ВЧ (10–1000 Гц) — Скорость', 'мм/с')
        ts_layout.addWidget(self.ts_acc_chart, 1)
        ts_layout.addWidget(self.ts_vel_chart, 1)
        main_layout.addLayout(ts_layout, 1)

        # === Ряд 4: Спектры с порогами ===
        spec_title = QLabel('Спектры')
        spec_title.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: bold;')
        main_layout.addWidget(spec_title)

        spec_layout = QHBoxLayout()
        spec_layout.setSpacing(10)
        self.spec_acc_chart = SpectrumChart(
            'НЧ спектр (0.1-10 Гц)', 'Гц', 'м/с²', (0, 30),
            thresholds=ACC_THRESHOLDS
        )
        self.spec_vel_chart = SpectrumChart(
            'ВЧ спектр (10-1000 Гц)', 'Гц', 'мм/с', (0, 1200),
            thresholds=VEL_THRESHOLDS
        )
        self.spec_hf_chart = SpectrumChart(
            'ВЧ(ф) спектр (0-12 кГц)', 'Гц', 'м/с²', (0, 12000)
        )
        spec_layout.addWidget(self.spec_acc_chart, 1)
        spec_layout.addWidget(self.spec_vel_chart, 1)
        spec_layout.addWidget(self.spec_hf_chart, 1)
        main_layout.addLayout(spec_layout, 1)

        # === Ряд 5: Таблица гармоник (ТОП-10 пиков) ===
        harmonics_title = QLabel('Таблица гармоник (ТОП-10 пиков)')
        harmonics_title.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: bold;')
        main_layout.addWidget(harmonics_title)

        self.harmonics_table = QTableWidget()
        self.harmonics_table.setColumnCount(4)
        self.harmonics_table.setHorizontalHeaderLabels(['Пик', 'Частота (Гц)', 'Амплитуда', 'Зона'])
        self.harmonics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # type: ignore[arg-type]
        self.harmonics_table.verticalHeader().setVisible(False)
        self.harmonics_table.setSelectionBehavior(QTableWidget.SelectRows)  # type: ignore[arg-type]
        self.harmonics_table.setSelectionMode(QTableWidget.SingleSelection)  # type: ignore[arg-type]
        self.harmonics_table.setMaximumHeight(180)
        self.harmonics_table.setStyleSheet(TABLE_STYLE + SCROLLBAR_STYLE)
        main_layout.addWidget(self.harmonics_table, 0)

    def set_parser(self, parser):
        """Установить парсер и обновить все данные."""
        self.parser = parser
        
        # Отладка
        import tempfile, datetime
        from pathlib import Path
        log_path = Path(tempfile.gettempdir()) / "vibrodiag_analysis_debug.log"
        
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== Analysis Debug {datetime.datetime.now()} ===\n")
            
            metrics = parser.get_turbine_metrics()
            f.write(f"Metrics: {metrics}\n")
            
            available = parser.get_available_sensors()
            f.write(f"Available sensors: {available}\n")
            
            self.metric_cards['power'].set_value(kw_to_mw(metrics['power_kw']))
            self.metric_cards['rpm'].set_value(metrics['generator_speed_rpm'])
            self.metric_cards['wind'].set_value(metrics['wind_speed_ms'])
            self.metric_cards['energy'].set_value(kwh_to_gwh(metrics['cumulative_power_kwh']))

            # Вычисляем зоны для всех датчиков
            self._compute_all_sensor_zones()
            f.write(f"Sensor zones: {self._sensor_zones}\n")

            # Обновляем индикаторы датчиков
            self._update_sensor_indicators()

            # Выбираем первый доступный датчик
            if available:
                self._current_sensor = available[0]
                f.write(f"Selecting sensor: {self._current_sensor}\n")
                self._select_sensor(self._current_sensor)
            else:
                f.write("No sensors available!\n")

    def _compute_all_sensor_zones(self):
        """Вычислить зоны ISO 10816 для всех датчиков."""
        if self.parser is None:
            return

        self._sensor_zones = {}
        analyzer = VibrationAnalyzer()

        for sensor_id in range(1, 9):
            data = self.parser.get_sensor_data(sensor_id)
            if not data:
                self._sensor_zones[sensor_id] = {'acc': '-', 'vel': '-', 'hf': '-'}
                continue

            zones = {}
            # НЧ (ускорение)
            if data.get('acceleration') is not None and len(data['acceleration']) > 0:
                rms = np.sqrt(np.mean(np.array(data['acceleration']) ** 2))
                zones['acc'] = analyzer.determine_zone_acc(rms)
            else:
                zones['acc'] = '-'

            # ВЧ (скорость)
            if data.get('velocity') is not None and len(data['velocity']) > 0:
                rms = np.sqrt(np.mean(np.array(data['velocity']) ** 2))
                zones['vel'] = analyzer.determine_zone_vel(rms)
            else:
                zones['vel'] = '-'

            # ВЧ(ф) (ускорение высокочастотное)
            if data.get('high_freq') is not None and len(data['high_freq']) > 0:
                rms = np.sqrt(np.mean(np.array(data['high_freq']) ** 2))
                zones['hf'] = analyzer.determine_zone_acc(rms)
            else:
                zones['hf'] = '-'

            self._sensor_zones[sensor_id] = zones

    def _update_sensor_indicators(self):
        """Обновить цвета индикаторов датчиков."""
        for sensor_id, zones in self._sensor_zones.items():
            indicator = self.sensor_indicators.get(sensor_id)
            if indicator:
                indicator.set_zones(zones['acc'], zones['vel'], zones['hf'])

    def _on_sensor_indicator_clicked(self, sensor_id: int):
        """Обработка клика по индикатору датчика."""
        self._select_sensor(sensor_id)

    def _select_sensor(self, sensor_id: int):
        """Выбрать датчик и обновить отображение."""
        if self.parser is None:
            return

        self._current_sensor = sensor_id

        # Обновляем выделение индикаторов
        for sid, indicator in self.sensor_indicators.items():
            indicator.setSelected(sid == sensor_id)

        # Загружаем данные датчика
        data = self.parser.get_sensor_data(sensor_id)
        if data is None:
            return

        try:
            self._update_time_series(data)
            self._update_spectrums(data)
            self._update_zone_indicators(data)
            self._update_harmonics_table(data)
        except Exception as e:
            show_critical(self, 'Ошибка', f'Ошибка при обработке датчика {sensor_id}:\n{str(e)}')

    def _on_sensor_changed(self, index):
        """Устаревший метод — больше не используется (combo box удалён)."""
        pass

    def _find_top_peaks(self, freqs, amps, top_n=10):
        """Найти ТОП-N пиков в спектре."""
        if len(amps) == 0:
            return []

        # Используем scipy.signal.find_peaks для поиска локальных максимумов
        from scipy.signal import find_peaks
        peaks, properties = find_peaks(amps, distance=max(1, len(amps) // 50), prominence=np.max(amps) * 0.05)

        # Сортируем по амплитуде
        peak_data = []
        for idx in peaks:
            peak_data.append({
                'frequency': freqs[idx],
                'amplitude': amps[idx]
            })

        peak_data.sort(key=lambda x: x['amplitude'], reverse=True)
        return peak_data[:top_n]

    def _update_harmonics_table(self, data):
        """Обновить таблицу гармоник (ТОП-10 пиков)."""
        self.harmonics_table.setRowCount(0)
        self._all_peaks = []  # Очищаем старые пики

        analyzer = VibrationAnalyzer()
        all_peaks = []

        # Собираем пики из всех трёх спектров
        # signal_type - название для таблицы
        # data_key - ключ данных (acceleration/velocity/high_freq)
        # fs_key - ключ частоты дискретизации
        # unit - единицы измерения
        for signal_type, data_key, fs_key, unit in [
            ('НЧ', 'acceleration', 'acceleration_fs', 'м/с²'),
            ('ВЧ', 'velocity', 'velocity_fs', 'мм/с'),
            ('ВЧ(ф)', 'high_freq', 'high_freq_fs', 'м/с²'),
        ]:
            signal_data = data.get(data_key)
            fs = data.get(fs_key)
            
            if signal_data is not None and fs and len(signal_data) > 0:
                try:
                    freqs, amps = analyzer.calculate_spectrum(np.array(signal_data), fs)
                    peaks = self._find_top_peaks(freqs, amps, top_n=5)
                    for peak in peaks:
                        # Определяем зону по амплитуде
                        zone = '-'
                        if unit == 'м/с²':
                            zone = analyzer.determine_zone_acc(peak['amplitude'])
                        elif unit == 'мм/с':
                            zone = analyzer.determine_zone_vel(peak['amplitude'])

                        all_peaks.append({
                            'signal_type': signal_type,
                            'frequency': peak['frequency'],
                            'amplitude': peak['amplitude'],
                            'zone': zone,
                            'unit': unit,
                            'amplitude_raw': peak['amplitude']  # Для сортировки
                        })
                except Exception:
                    # Если не удалось вычислить спектр, пропускаем
                    continue

        # Сортируем все пики по амплитуде
        all_peaks.sort(key=lambda x: x['amplitude_raw'], reverse=True)
        top_peaks = all_peaks[:10]

        # Сохраняем для взаимодействия с графиками
        self._all_peaks = top_peaks

        # Заполняем таблицу
        for row_idx, peak in enumerate(top_peaks):
            self.harmonics_table.insertRow(row_idx)

            # Пик №
            item0 = QTableWidgetItem(f"{row_idx + 1}")
            item0.setTextAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
            item0.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.harmonics_table.setItem(row_idx, 0, item0)

            # Тип сигнала
            item1 = QTableWidgetItem(peak['signal_type'])
            item1.setTextAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
            item1.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.harmonics_table.setItem(row_idx, 1, item1)

            # Частота
            item2 = QTableWidgetItem(f"{peak['frequency']:.2f}")
            item2.setTextAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
            item2.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.harmonics_table.setItem(row_idx, 2, item2)

            # Амплитуда + зона
            zone_color = ZONE_COLORS.get(peak['zone'], COLOR_TEXT_TERTIARY)
            item3 = QTableWidgetItem(f"{peak['amplitude']:.4f} {peak['unit']}")
            item3.setTextAlignment(Qt.AlignCenter)  # type: ignore[arg-type]
            item3.setForeground(QColor(zone_color))
            self.harmonics_table.setItem(row_idx, 3, item3)

        # Сохраняем пики для отображения на графиках (с группировкой по типу сигнала)
        self._current_peaks = {
            'НЧ': [p for p in top_peaks if p['signal_type'] == 'НЧ'],
            'ВЧ': [p for p in top_peaks if p['signal_type'] == 'ВЧ'],
            'ВЧ(ф)': [p for p in top_peaks if p['signal_type'] == 'ВЧ(ф)'],
        }

    def _update_time_series(self, data):
        """Обновить графики временных рядов."""
        if data.get('acceleration') is not None and data.get('acceleration_time') is not None:
            acc = np.array(data['acceleration'])
            t_acc = np.array(data['acceleration_time'])
            n = min(len(acc), len(t_acc))
            if n > 0:
                self.ts_acc_chart.set_data(t_acc[:n], acc[:n])
            else:
                self.ts_acc_chart.clear()
        else:
            self.ts_acc_chart.clear()

        if data.get('velocity') is not None and data.get('velocity_time') is not None:
            vel = np.array(data['velocity'])
            t_vel = np.array(data['velocity_time'])
            n = min(len(vel), len(t_vel))
            if n > 0:
                self.ts_vel_chart.set_data(t_vel[:n], vel[:n])
            else:
                self.ts_vel_chart.clear()
        else:
            self.ts_vel_chart.clear()

    def _update_spectrums(self, data):
        """Обновить графики спектров с порогами и маркерами пиков."""
        analyzer = VibrationAnalyzer()

        # НЧ спектр (0.1-10 Гц)
        if data.get('acceleration') is not None and data.get('acceleration_fs'):
            acc = np.array(data['acceleration'])
            fs = data['acceleration_fs']
            if len(acc) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(acc, fs)
                mask = (freqs >= 0.1) & (freqs <= 10)
                freq_masked = freqs[mask]
                amps_masked = amps[mask]
                # Передаем ТОЛЬКО НЧ пики
                nch_peaks = self._current_peaks.get('НЧ', []) if hasattr(self, '_current_peaks') else []
                peak_freqs = [p['frequency'] for p in nch_peaks]
                peak_nums = [p['amplitude_raw'] for p in nch_peaks]  # Используем как временный ID
                self.spec_acc_chart.set_data(freq_masked, amps_masked, peak_frequencies=peak_freqs)
            else:
                self.spec_acc_chart.clear()
        else:
            self.spec_acc_chart.clear()

        # ВЧ спектр (10-1000 Гц)
        if data.get('velocity') is not None and data.get('velocity_fs'):
            vel = np.array(data['velocity'])
            fs = data['velocity_fs']
            if len(vel) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(vel, fs)
                mask = (freqs >= 10) & (freqs <= 1200)
                freq_masked = freqs[mask]
                amps_masked = amps[mask]
                # Передаем ТОЛЬКО ВЧ пики
                vch_peaks = self._current_peaks.get('ВЧ', []) if hasattr(self, '_current_peaks') else []
                peak_freqs = [p['frequency'] for p in vch_peaks]
                self.spec_vel_chart.set_data(freq_masked, amps_masked, peak_frequencies=peak_freqs)
            else:
                self.spec_vel_chart.clear()
        else:
            self.spec_vel_chart.clear()

        # ВЧ(ф) спектр (0-12 кГц)
        if data.get('high_freq') is not None and data.get('high_freq_fs'):
            hf = np.array(data['high_freq'])
            fs = data['high_freq_fs']
            if len(hf) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(hf, fs)
                mask = (freqs >= 0) & (freqs <= 12000)
                freq_masked = freqs[mask]
                amps_masked = amps[mask]
                # Передаем ТОЛЬКО ВЧ(ф) пики
                vchf_peaks = self._current_peaks.get('ВЧ(ф)', []) if hasattr(self, '_current_peaks') else []
                peak_freqs = [p['frequency'] for p in vchf_peaks]
                self.spec_hf_chart.set_data(freq_masked, amps_masked, peak_frequencies=peak_freqs)
            else:
                self.spec_hf_chart.clear()
        else:
            self.spec_hf_chart.clear()

    def _update_zone_indicators(self, data):
        """Обновить индикаторы зон ISO 10816."""
        analyzer = VibrationAnalyzer()

        if data.get('acceleration') is not None and len(data['acceleration']) > 0:
            rms = np.sqrt(np.mean(np.array(data['acceleration']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            self.zone_indicators['acc'].set_zone(zone, rms, 'м/с²')
        else:
            self.zone_indicators['acc'].set_zone('-')

        if data.get('velocity') is not None and len(data['velocity']) > 0:
            rms = np.sqrt(np.mean(np.array(data['velocity']) ** 2))
            zone = analyzer.determine_zone_vel(rms)
            self.zone_indicators['vel'].set_zone(zone, rms, 'мм/с')
        else:
            self.zone_indicators['vel'].set_zone('-')

        if data.get('high_freq') is not None and len(data['high_freq']) > 0:
            rms = np.sqrt(np.mean(np.array(data['high_freq']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            self.zone_indicators['hf'].set_zone(zone, rms, 'м/с²')
        else:
            self.zone_indicators['hf'].set_zone('-')

    def _get_current_sensor_id(self) -> int:
        """Получить ID текущего выбранного датчика."""
        return self._current_sensor

    def _export_csv(self):
        """Экспорт данных текущего датчика в CSV."""
        if self.parser is None:
            show_critical(self, 'Ошибка', 'Нет данных для экспорта. Загрузите файл.')
            return

        sensor_id = self._get_current_sensor_id()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в CSV", f"sensor_{sensor_id}_export.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        from .export_thread import ExportWorker
        self._run_export_worker('csv', sensor_id, file_path)

    def _export_excel(self):
        """Экспорт данных текущего датчика в Excel."""
        if self.parser is None:
            show_critical(self, 'Ошибка', 'Нет данных для экспорта. Загрузите файл.')
            return

        sensor_id = self._get_current_sensor_id()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт в Excel", f"sensor_{sensor_id}_export.xlsx",
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return

        self._run_export_worker('excel', sensor_id, file_path)

    def _export_pdf(self):
        """Сформировать PDF-отчёт."""
        if self.parser is None:
            show_critical(self, 'Ошибка', 'Нет данных для экспорта. Загрузите файл.')
            return

        sensor_id = self._get_current_sensor_id()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF-отчёт", f"vibrodiag_report.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not file_path:
            return

        self._run_pdf_worker(sensor_id, file_path)

    def _run_export_worker(self, export_type: str, sensor_id: int, file_path: str):
        """Запустить поток экспорта с прогресс-диалогом."""
        progress = QProgressDialog("Экспорт данных...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)  # type: ignore[attr-defined]
        progress.setWindowTitle("Экспорт")
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #2A2A2A;
                text-align: center;
                color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 4px;
                padding: 4px 12px;
            }
        """)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        from .export_thread import ExportWorker
        self.export_worker = ExportWorker(export_type, self.parser, sensor_id, file_path)
        self.export_worker.progress.connect(lambda p, msg: (progress.setValue(p), progress.setLabelText(msg)))  # type: ignore[func-returns-value]
        self.export_worker.finished.connect(
            lambda ok, msg: self._on_export_finished(ok, msg, progress)
        )
        progress.canceled.connect(self.export_worker.terminate)
        self.export_worker.start()

    def _on_export_finished(self, success: bool, message: str, progress_dialog):
        """Обработчик завершения экспорта."""
        progress_dialog.setValue(100)
        progress_dialog.close()

        if success:
            from .styled_message_box import show_info
            show_info(self, "Экспорт завершён", message)
        else:
            from .styled_message_box import show_critical
            show_critical(self, "Ошибка экспорта", message)

    def _run_pdf_worker(self, sensor_id: int, file_path: str):
        """Запустить генерацию PDF с прогресс-диалогом."""
        progress = QProgressDialog("Формирование PDF-отчёта...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)  # type: ignore[attr-defined]
        progress.setWindowTitle("PDF-отчёт")
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: #1A1A1A;
                color: #FFFFFF;
            }
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 4px;
                background-color: #2A2A2A;
                text-align: center;
                color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #000000;
                border-radius: 4px;
                padding: 4px 12px;
            }
        """)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        from .pdf_report_thread import PDFReportWorker
        self.pdf_worker = PDFReportWorker(self.parser, sensor_id, file_path)
        self.pdf_worker.progress.connect(lambda p, msg: (progress.setValue(p), progress.setLabelText(msg)))  # type: ignore[func-returns-value]
        self.pdf_worker.finished.connect(
            lambda ok, msg: self._on_export_finished(ok, msg, progress)
        )
        progress.canceled.connect(self.pdf_worker.terminate)
        self.pdf_worker.start()
