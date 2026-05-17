# -*- coding: utf-8 -*-
"""
Экран анализа данных v1.2
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt

from .metric_card import MetricCard
from .charts.time_series_chart import TimeSeriesChart
from .charts.spectrum_chart import SpectrumChart
from ..utils.conversions import kw_to_mw, kwh_to_gwh
from ..utils.vibration_analysis import VibrationAnalyzer


class ZoneIndicator(QFrame):
    ZONE_COLORS = {
        'A': '#00C853',
        'B': '#FFD600',
        'C': '#FF6D00',
        'D': '#DD2C00',
        '-': '#424242',
    }

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 80)
        self.setStyleSheet("""
            ZoneIndicator {
                background-color: #2D2D2D;
                border-radius: 8px;
                border: 2px solid #424242;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet('color: #B0B0B0; font-size: 10px;')
        self.title_label.setAlignment(Qt.AlignCenter)

        self.zone_label = QLabel('-')
        self.zone_label.setStyleSheet('color: #FFFFFF; font-size: 24px; font-weight: bold;')
        self.zone_label.setAlignment(Qt.AlignCenter)

        self.rms_label = QLabel(u'—')
        self.rms_label.setStyleSheet('color: #888888; font-size: 9px;')
        self.rms_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.title_label)
        layout.addWidget(self.zone_label)
        layout.addWidget(self.rms_label)

    def set_zone(self, zone, rms_value=0.0, unit='мм/с'):
        zone = zone if zone in self.ZONE_COLORS else '-'
        color = self.ZONE_COLORS[zone]
        self.zone_label.setText(zone)
        self.zone_label.setStyleSheet(
            f'color: {color}; font-size: 24px; font-weight: bold;'
        )
        self.rms_label.setText(
            f'СКЗ: {rms_value:.3f} {unit}' if zone != '-' else 'Нет данных'
        )
        self.setStyleSheet(f"""
            ZoneIndicator {{
                background-color: #2D2D2D;
                border-radius: 8px;
                border: 2px solid {color};
            }}
        """)


class AnalysisDataScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #1E1E1E;")
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # === Ряд 1: Метрики турбины ===
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.metric_cards = {
            'power': MetricCard('Мощность', 0.0, 'МВт'),
            'rpm': MetricCard('Частота вращения', 0.0, 'об/мин'),
            'wind': MetricCard('Скорость ветра', 0.0, 'м/с'),
            'energy': MetricCard('Накопленная выработка', 0.0, 'ГВт·ч'),
        }
        for card in self.metric_cards.values():
            metrics_layout.addWidget(card, 1)
        main_layout.addLayout(metrics_layout)

        # === Ряд 2: Датчик + Зоны ISO 10816 ===
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)

        # Датчик (слева)
        sensor_layout = QHBoxLayout()
        sensor_layout.setSpacing(8)
        sensor_label = QLabel('Датчик:')
        sensor_label.setStyleSheet('color: #FFFFFF; font-size: 12px;')
        self.sensor_combo = QComboBox()
        self.sensor_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2D2D2D;
                color: #FFFFFF;
                selection-background-color: #00C853;
            }
        """)
        self.sensor_combo.currentIndexChanged.connect(self._on_sensor_changed)
        sensor_layout.addWidget(sensor_label)
        sensor_layout.addWidget(self.sensor_combo)
        sensor_layout.addStretch()
        controls_layout.addLayout(sensor_layout)

        # Зоны ISO 10816 (справа)
        zones_wrapper = QHBoxLayout()
        zones_wrapper.setSpacing(8)
        zones_title = QLabel('Зоны ISO 10816')
        zones_title.setStyleSheet('color: #FFFFFF; font-size: 12px; font-weight: bold;')
        zones_wrapper.addWidget(zones_title)

        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(8)
        self.zone_indicators = {
            'acc': ZoneIndicator('НЧ Acc'),
            'vel': ZoneIndicator('ВЧ Vel'),
            'hf': ZoneIndicator('ВЧ(ф)'),
        }
        for zi in self.zone_indicators.values():
            zones_layout.addWidget(zi)
        zones_wrapper.addLayout(zones_layout)
        zones_wrapper.addStretch()
        controls_layout.addLayout(zones_wrapper, 1)

        main_layout.addLayout(controls_layout)

        # === Ряд 3: Временные ряды ===
        ts_title = QLabel('Временные ряды')
        ts_title.setStyleSheet('color: #FFFFFF; font-size: 12px; font-weight: bold;')
        main_layout.addWidget(ts_title)

        ts_layout = QHBoxLayout()
        ts_layout.setSpacing(12)
        self.ts_acc_chart = TimeSeriesChart('НЧ (0.1–10 Гц) — Ускорение', 'м/с²')
        self.ts_vel_chart = TimeSeriesChart('ВЧ (10–1000 Гц) — Скорость', 'мм/с')
        ts_layout.addWidget(self.ts_acc_chart, 1)
        ts_layout.addWidget(self.ts_vel_chart, 1)
        main_layout.addLayout(ts_layout, 2)

        # === Ряд 4: Спектры ===
        spec_title = QLabel('Спектры')
        spec_title.setStyleSheet('color: #FFFFFF; font-size: 12px; font-weight: bold;')
        main_layout.addWidget(spec_title)

        spec_layout = QHBoxLayout()
        spec_layout.setSpacing(12)
        self.spec_acc_chart = SpectrumChart('НЧ спектр', 'Гц', 'м/с²', (0, 30))
        self.spec_vel_chart = SpectrumChart('ВЧ спектр', 'Гц', 'мм/с', (0, 1200))
        self.spec_hf_chart = SpectrumChart('ВЧ(ф) спектр', 'Гц', 'м/с²', (0, 12000))
        spec_layout.addWidget(self.spec_acc_chart, 1)
        spec_layout.addWidget(self.spec_vel_chart, 1)
        spec_layout.addWidget(self.spec_hf_chart, 1)
        main_layout.addLayout(spec_layout, 2)

    def set_parser(self, parser):
        self.parser = parser
        metrics = parser.get_turbine_metrics()
        self.metric_cards['power'].set_value(kw_to_mw(metrics['power_kw']))
        self.metric_cards['rpm'].set_value(metrics['generator_speed_rpm'])
        self.metric_cards['wind'].set_value(metrics['wind_speed_ms'])
        self.metric_cards['energy'].set_value(kwh_to_gwh(metrics['cumulative_power_kwh']))

        self.sensor_combo.blockSignals(True)
        self.sensor_combo.clear()
        for sid in parser.get_available_sensors():
            self.sensor_combo.addItem(f'Датчик {sid}', sid)
        self.sensor_combo.blockSignals(False)

        if self.sensor_combo.count() > 0:
            self._on_sensor_changed(0)

    def _on_sensor_changed(self, index):
        if self.parser is None or self.sensor_combo.count() == 0:
            return
        sensor_id = self.sensor_combo.currentData()
        data = self.parser.get_sensor_data(sensor_id)
        if data is None:
            return
        try:
            self._update_time_series(data)
            self._update_spectrums(data)
            self._update_zone_indicators(data)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при обработке файла:\n{str(e)}')

    def _update_time_series(self, data):
        if data['acceleration'] is not None and data['acceleration_time'] is not None:
            acc = np.array(data['acceleration'])
            t_acc = np.array(data['acceleration_time'])
            n = min(len(acc), len(t_acc))
            self.ts_acc_chart.set_data(t_acc[:n], acc[:n])
        else:
            self.ts_acc_chart.clear_data()

        if data['velocity'] is not None and data['velocity_time'] is not None:
            vel = np.array(data['velocity'])
            t_vel = np.array(data['velocity_time'])
            n = min(len(vel), len(t_vel))
            self.ts_vel_chart.set_data(t_vel[:n], vel[:n])
        else:
            self.ts_vel_chart.clear_data()

    def _update_spectrums(self, data):
        analyzer = VibrationAnalyzer()

        if data['acceleration'] is not None and data['acceleration_fs']:
            acc = np.array(data['acceleration'])
            fs = data['acceleration_fs']
            if len(acc) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(acc, fs)
                mask = freqs <= 30
                self.spec_acc_chart.set_data(freqs[mask], amps[mask])
            else:
                self.spec_acc_chart.clear_data()
        else:
            self.spec_acc_chart.clear_data()

        if data['velocity'] is not None and data['velocity_fs']:
            vel = np.array(data['velocity'])
            fs = data['velocity_fs']
            if len(vel) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(vel, fs)
                mask = freqs <= 1200
                self.spec_vel_chart.set_data(freqs[mask], amps[mask])
            else:
                self.spec_vel_chart.clear_data()
        else:
            self.spec_vel_chart.clear_data()

        if data['high_freq'] is not None and data['high_freq_fs']:
            hf = np.array(data['high_freq'])
            fs = data['high_freq_fs']
            if len(hf) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(hf, fs)
                mask = freqs <= 12000
                self.spec_hf_chart.set_data(freqs[mask], amps[mask])
            else:
                self.spec_hf_chart.clear_data()
        else:
            self.spec_hf_chart.clear_data()

    def _update_zone_indicators(self, data):
        analyzer = VibrationAnalyzer()

        if data['acceleration'] is not None:
            rms = np.sqrt(np.mean(np.array(data['acceleration']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            self.zone_indicators['acc'].set_zone(zone, rms, 'm/s²')
        else:
            self.zone_indicators['acc'].set_zone('-')

        if data['velocity'] is not None:
            rms = np.sqrt(np.mean(np.array(data['velocity']) ** 2))
            zone = analyzer.determine_zone_vel(rms)
            self.zone_indicators['vel'].set_zone(zone, rms, 'mm/s')
        else:
            self.zone_indicators['vel'].set_zone('-')

        if data['high_freq'] is not None:
            rms = np.sqrt(np.mean(np.array(data['high_freq']) ** 2))
            zone = analyzer.determine_zone_acc(rms)
            self.zone_indicators['hf'].set_zone(zone, rms, 'm/s²')
        else:
            self.zone_indicators['hf'].set_zone('-')
