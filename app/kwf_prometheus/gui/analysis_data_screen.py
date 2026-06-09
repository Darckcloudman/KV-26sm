# -*- coding: utf-8 -*-
"""
Экран анализа данных v1.4 — с индикаторами датчиков, порогами и таблицей гармоник
"""

import numpy as np
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QFrame, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

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
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.zone_label = QLabel('-')
        self.zone_label.setStyleSheet(f'color: {COLOR_TEXT_PRIMARY}; font-size: 24px; font-weight: bold;')
        self.zone_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rms_label = QLabel('—')
        self.rms_label.setStyleSheet(f'color: {COLOR_TEXT_TERTIARY}; font-size: 9px;')
        self.rms_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
            sec.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.parser = None
        self._current_sensor = 1
        self._sensor_zones = {}  # {sensor_id: {'acc': zone, 'vel': zone, 'hf': zone}}
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

        # Индикаторы 8 датчиков с разделением на группы (слева)
        sensors_wrapper = QVBoxLayout()
        sensors_wrapper.setSpacing(6)
        
        # Группа 1: Редуктор (датчики 1-5)
        gearbox_layout = QHBoxLayout()
        gearbox_layout.setSpacing(4)
        gearbox_label = QLabel('Редуктор:')
        gearbox_label.setStyleSheet(f'color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: bold;')
        gearbox_layout.addWidget(gearbox_label)
        
        self.sensor_indicators = {}
        for sensor_id in range(1, 6):
            indicator = SensorStatusIndicator(sensor_id, self)
            indicator.clicked.connect(self._on_sensor_indicator_clicked)
            gearbox_layout.addWidget(indicator)
            self.sensor_indicators[sensor_id] = indicator
        
        sensors_wrapper.addLayout(gearbox_layout)
        
        # Группа 2: Генератор (датчики 6-8)
        generator_layout = QHBoxLayout()
        generator_layout.setSpacing(4)
        generator_label = QLabel('Генератор:')
        generator_label.setStyleSheet(f'color: {COLOR_TEXT_SECONDARY}; font-size: 10px; font-weight: bold;')
        generator_layout.addWidget(generator_label)
        
        for sensor_id in range(6, 9):
            indicator = SensorStatusIndicator(sensor_id, self)
            indicator.clicked.connect(self._on_sensor_indicator_clicked)
            generator_layout.addWidget(indicator)
            self.sensor_indicators[sensor_id] = indicator
        
        sensors_wrapper.addLayout(generator_layout)
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
            'НЧ спектр (0.1-10 Гц)', 'Гц', 'м/с²', (0.1, 10),
            thresholds=ACC_THRESHOLDS
        )
        self.spec_vel_chart = SpectrumChart(
            'ВЧ спектр (10-1000 Гц)', 'Гц', 'мм/с', (10, 1000),
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
        self.harmonics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.harmonics_table.verticalHeader().setVisible(False)
        self.harmonics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.harmonics_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.harmonics_table.setMaximumHeight(180)
        self.harmonics_table.setStyleSheet(TABLE_STYLE + SCROLLBAR_STYLE)
        self.harmonics_table.itemSelectionChanged.connect(self._on_harmonics_row_selected)
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

    def _find_top_peaks(self, freqs, amps, top_n=10, max_freq_limit=None):
        """Найти ТОП-N пиков в спектре.
        
        Args:
            freqs: массив частот
            amps: массив амплитуд
            top_n: количество пиков
            max_freq_limit: максимальная частота (Nyquist limit)
        """
        if len(amps) == 0:
            return []

        # Фильтруем по максимальной частоте (теорема Найквиста)
        if max_freq_limit is not None:
            mask = freqs <= max_freq_limit
            freqs = freqs[mask]
            amps = amps[mask]
            if len(amps) == 0:
                return []

        # Для малых массивов (< 50 точек) используем простую сортировку по амплитуде
        if len(amps) < 50:
            peak_data = []
            for i in range(len(freqs)):
                peak_data.append({
                    'frequency': freqs[i],
                    'amplitude': amps[i]
                })
            peak_data.sort(key=lambda x: x['amplitude'], reverse=True)
            return peak_data[:top_n]

        # Для больших массивов используем scipy.signal.find_peaks
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

        analyzer = VibrationAnalyzer()
        all_peaks = []

        # Собираем пики из всех трёх спектров с диапазонами частот
        signal_configs = [
            # (название, ключ данных, ключ Fs, единицы, пороги, min_freq, max_freq)
            ('НЧ', 'acceleration', 'acceleration_fs', 'м/с²', ACC_THRESHOLDS, 0.1, 10),
            ('ВЧ', 'velocity', 'velocity_fs', 'мм/с', VEL_THRESHOLDS, 10, 1000),
            ('ВЧ(ф)', 'high_freq', 'high_freq_fs', 'м/с²', ACC_THRESHOLDS, 0, 12000),
        ]
        
        for signal_name, signal_key, fs_key, unit, thresholds, min_f, max_f in signal_configs:
            signal_data = data.get(signal_key)
            fs = data.get(fs_key)
            
            if signal_data is not None and fs and len(signal_data) > 0:
                freqs, amps = analyzer.calculate_spectrum(np.array(signal_data), fs)
                # Ограничиваем пики по диапазону фильтра + Найквисту
                nyquist_freq = fs / 2
                effective_max = min(max_f, nyquist_freq)
                peaks = self._find_top_peaks(freqs, amps, top_n=5, max_freq_limit=effective_max)
                
                # Дополнительный фильтр по минимальной частоте
                peaks = [p for p in peaks if p['frequency'] >= min_f]
                
                print(f"[DEBUG] {signal_name}: Fs={fs:.0f} Hz, Nyquist={nyquist_freq:.0f} Hz, range={min_f}-{effective_max:.0f} Hz, found {len(peaks)} peaks")
                for p in peaks[:3]:
                    print(f"[DEBUG]   - {p['frequency']:.2f} Hz, amp={p['amplitude']:.6f}")
                
                for peak in peaks:
                    zone = '-'
                    if unit == 'м/с²':
                        zone = analyzer.determine_zone_acc(peak['amplitude'])
                    elif unit == 'мм/с':
                        zone = analyzer.determine_zone_vel(peak['amplitude'])

                    all_peaks.append({
                        'signal_type': signal_name,  # НЧ, ВЧ, или ВЧ(ф)
                        'frequency': peak['frequency'],
                        'amplitude': peak['amplitude'],
                        'zone': zone,
                        'unit': unit,
                        'freq_range': (min_f, max_f)  # Диапазон фильтра
                    })

        # Сортируем все пики по амплитуде
        all_peaks.sort(key=lambda x: x['amplitude'], reverse=True)
        top_peaks = all_peaks[:10]

        # Заполняем таблицу (4 колонки: Пик, Тип, Частота, Амплитуда+Зона)
        for row_idx, peak in enumerate(top_peaks):
            self.harmonics_table.insertRow(row_idx)

            # Пик №
            item0 = QTableWidgetItem(f"{row_idx + 1}")
            item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item0.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.harmonics_table.setItem(row_idx, 0, item0)

            # Тип сигнала уже определён из signal_configs и сохранён в signal_type
            # Используем его напрямую
            signal_type_display = peak['signal_type']

            item1 = QTableWidgetItem(signal_type_display)
            item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item1.setForeground(QColor(COLOR_TEXT_SECONDARY))
            self.harmonics_table.setItem(row_idx, 1, item1)

            # Частота
            item2 = QTableWidgetItem(f"{peak['frequency']:.2f}")
            item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item2.setForeground(QColor(COLOR_TEXT_PRIMARY))
            self.harmonics_table.setItem(row_idx, 2, item2)

            # Амплитуда + зона
            zone_color = ZONE_COLORS.get(peak['zone'], COLOR_TEXT_TERTIARY)
            item3 = QTableWidgetItem(f"{peak['amplitude']:.4f} {peak['unit']}")
            item3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item3.setForeground(QColor(zone_color))
            self.harmonics_table.setItem(row_idx, 3, item3)

        # Сохраняем все пики таблицы для последующего отображения
        self._all_table_peaks = top_peaks
        
        # Добавляем глобальный номер пика (из таблицы)
        for idx, peak in enumerate(top_peaks):
            peak['global_number'] = idx + 1
        
        # Фильтруем пики по диапазонам частот для каждого графика
        # НЧ спектр: 0.1-10 Гц, ВЧ спектр: 10-1000 Гц, ВЧ(ф) спектр: 0-12000 Гц
        nch_peaks = [p for p in top_peaks if p['signal_type'] == 'НЧ' and 0.1 <= p['frequency'] <= 10]
        vch_peaks = [p for p in top_peaks if p['signal_type'] == 'ВЧ' and 10 <= p['frequency'] <= 1000]
        vchf_peaks = [p for p in top_peaks if p['signal_type'] == 'ВЧ(ф)' and 0 <= p['frequency'] <= 12000]
        
        self._current_peaks = {
            'НЧ': nch_peaks,
            'ВЧ': vch_peaks,
            'ВЧ(ф)': vchf_peaks,
        }

        # Выводим в лог файл с UTF-8, а не в консоль
        # print(f"\n[UPDATE] Таблица гармоник: {len(top_peaks)} пиков")
        # for i, p in enumerate(top_peaks):
        #     print(f"[UPDATE]   [{i+1}] {p['signal_type']:6} {p['frequency']:8.2f} Гц  amp={p['amplitude']:.6f}  unit={p['unit']}")
        # print(f"[UPDATE] Фильтр для отображения: НЧ={len(nch_peaks)}, ВЧ={len(vch_peaks)}, ВЧ(ф)={len(vchf_peaks)}")

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
        """Обновить графики спектров с порогами (без автоматических линий пиков)."""
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
                # Сохраняем данные для последующего отображения пика
                self._spec_acc_freq = freq_masked
                self._spec_acc_amps = amps_masked
                # print(f"[DEBUG] НЧ: data_len={len(freq_masked)}, freq_range=...")
                self.spec_acc_chart.set_data(freq_masked, amps_masked)
            else:
                self.spec_acc_chart.clear()
        else:
            self.spec_acc_chart.clear()

        # ВЧ спектр (10-1000 Гц) - но адаптируем под реальные данные
        if data.get('velocity') is not None and data.get('velocity_fs'):
            vel = np.array(data['velocity'])
            fs = data['velocity_fs']
            if len(vel) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(vel, fs)
                mask = (freqs >= 10) & (freqs <= 1000)
                freq_masked = freqs[mask]
                amps_masked = amps[mask]
                # Сохраняем данные для последующего отображения пика
                self._spec_vel_freq = freq_masked
                self._spec_vel_amps = amps_masked
                # Устанавливаем диапазон графика с запасом 20% для отображения пиков
                if len(freq_masked) > 0:
                    max_freq = np.max(freq_masked)
                    self.spec_vel_chart.plot_widget.setXRange(10, max_freq * 1.2, padding=0.05)
                print(f"[UPDATE] ВЧ спектр: {len(freq_masked)} точек, диапазон {np.min(freq_masked):.2f}-{np.max(freq_masked):.2f} Hz")
                self.spec_vel_chart.set_data(freq_masked, amps_masked)
            else:
                print(f"[UPDATE] ВЧ: нет данных (vel={len(vel) if 'vel' in dir() else 0}, fs={fs})")
                self.spec_vel_chart.clear()
        else:
            print(f"[UPDATE] ВЧ: velocity или velocity_fs отсутствует")
            self.spec_vel_chart.clear()

        # ВЧ(ф) спектр (0-12 кГц)
        if data.get('high_freq') is not None and data.get('high_freq_fs'):
            hf = np.array(data['high_freq'])
            fs = data.get('high_freq_fs')
            if len(hf) > 0 and fs > 0:
                freqs, amps = analyzer.calculate_spectrum(hf, fs)
                # Nyquist limit
                nyquist = fs / 2
                mask = (freqs >= 0) & (freqs <= nyquist)
                freq_masked = freqs[mask]
                amps_masked = amps[mask]
                # Сохраняем данные для последующего отображения пика
                self._spec_hf_freq = freq_masked
                self._spec_hf_amps = amps_masked
                # Устанавливаем диапазон графика с запасом 5%
                if len(freq_masked) > 0:
                    max_freq = np.max(freq_masked)
                    # Показываем до max частоты данных + 5%
                    x_max = max_freq * 1.05
                    self.spec_hf_chart.plot_widget.setXRange(0, x_max, padding=0.05)
                    print(f"[UPDATE] VCh(f) spektr: {len(freq_masked)} tochek, diapazon {np.min(freq_masked):.2f}-{max_freq:.2f} Hz, Fs={fs:.0f} Hz, Nyquist={nyquist:.0f} Hz, X_max={x_max:.0f} Hz")
                else:
                    print(f"[UPDATE] VCh(f): pustoy spektr posle filtratsii")
                self.spec_hf_chart.set_data(freq_masked, amps_masked)
            else:
                print(f"[UPDATE] VCh(f): net dannyh (hf={len(hf) if 'hf' in dir() else 0}, fs={fs})")
                self.spec_hf_chart.clear()
        else:
            print(f"[UPDATE] VCh(f): high_freq ili high_freq_fs otsutstvuet")
            self.spec_hf_chart.clear()

    def _on_harmonics_row_selected(self):
        """Обработка выбора строки в таблице гармоник - показать линию пика."""
        selected_rows = self.harmonics_table.selectedItems()
        if not selected_rows:
            # Если ничего не выбрано, очищаем все линии
            self.spec_acc_chart.clear_peak_markers()
            self.spec_vel_chart.clear_peak_markers()
            self.spec_hf_chart.clear_peak_markers()
            return

        # Получаем номер строки
        row = selected_rows[0].row()
        
        # Получаем данные пика напрямую из таблицы (по строке)
        if not hasattr(self, '_all_table_peaks') or row >= len(self._all_table_peaks):
            print(f"[DEBUG] Ошибка: строка {row} вне диапазона peaks ({len(self._all_table_peaks) if hasattr(self, '_all_table_peaks') else 0})")
            return

        peak = self._all_table_peaks[row]
        peak_freq = peak['frequency']
        peak_number = peak.get('global_number', row + 1)
        signal_type = peak['signal_type']
        
        print(f"\n[DEBUG] ========== Клик по пику #{peak_number}: {signal_type}, {peak_freq:.2f} Hz ==========")
        
        # Очищаем все линии перед отображением нового пика
        self.spec_acc_chart.clear_peak_markers()
        self.spec_vel_chart.clear_peak_markers()
        self.spec_hf_chart.clear_peak_markers()
        
        # Определяем, на каком графике показывать пик по фактическому диапазону данных
        target_chart = None
        freq_data = None
        amp_data = None
        
        # Проверяем каждый график на соответствие частоте пика
        acc_freq = getattr(self, '_spec_acc_freq', None)
        vel_freq = getattr(self, '_spec_vel_freq', None)
        hf_freq = getattr(self, '_spec_hf_freq', None)
        
        # Проверяем НЧ график (0.1-10 Гц)
        if acc_freq is not None and len(acc_freq) > 0:
            acc_min, acc_max = np.min(acc_freq), np.max(acc_freq)
            if acc_min * 0.9 <= peak_freq <= acc_max * 1.2:
                target_chart = self.spec_acc_chart
                freq_data = acc_freq
                amp_data = getattr(self, '_spec_acc_amps', None)
                print(f"[DEBUG] Пик {peak_freq:.2f} Hz -> НЧ график (диапазон {acc_min:.2f}-{acc_max:.2f})")
        
        # Проверяем ВЧ график (10-1000 Гц)
        if target_chart is None and vel_freq is not None and len(vel_freq) > 0:
            vel_min, vel_max = np.min(vel_freq), np.max(vel_freq)
            if vel_min * 0.9 <= peak_freq <= vel_max * 1.2:
                target_chart = self.spec_vel_chart
                freq_data = vel_freq
                amp_data = getattr(self, '_spec_vel_amps', None)
                print(f"[DEBUG] Пик {peak_freq:.2f} Hz -> ВЧ график (диапазон {vel_min:.2f}-{vel_max:.2f})")
        
        # Проверяем ВЧ(ф) график (0-12000 Гц)
        if target_chart is None and hf_freq is not None and len(hf_freq) > 0:
            hf_min, hf_max = np.min(hf_freq), np.max(hf_freq)
            # Пик должен быть в диапазоне данных (с запасом 10%)
            # НЕ показываем пик если частота выше максимума данных
            if hf_min * 0.9 <= peak_freq <= hf_max * 1.1:
                target_chart = self.spec_hf_chart
                freq_data = hf_freq
                amp_data = getattr(self, '_spec_hf_amps', None)
                print(f"[DEBUG] Pik {peak_freq:.2f} Hz -> VCh(f) grafik (diapazon {hf_min:.2f}-{hf_max:.2f})")
            else:
                print(f"[DEBUG] Pik {peak_freq:.2f} Hz NE POPADAET v diapazon VCh(f) (max={hf_max:.2f})!")
        
        # Показываем пик на найденном графике
        if target_chart is not None:
            target_chart.show_single_peak(peak_freq, peak_number, freq_data, amp_data)
        else:
            print(f"[DEBUG] Pik {peak_freq:.2f} Hz ne popadaet ni v odin diapazon!")

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
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        progress = QProgressDialog("Экспорт данных...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
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
        self.export_worker = ExportWorker(export_type, self.parser, sensor_id, Path(file_path))
        self.export_worker.progress.connect(lambda p, msg: progress.setValue(p) or progress.setLabelText(msg))
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
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        progress = QProgressDialog("Формирование PDF-отчёта...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
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
        self.pdf_worker = PDFReportWorker(self.parser, sensor_id, Path(file_path))
        self.pdf_worker.progress.connect(lambda p, msg: progress.setValue(p) or progress.setLabelText(msg))
        self.pdf_worker.finished.connect(
            lambda ok, msg: self._on_export_finished(ok, msg, progress)
        )
        progress.canceled.connect(self.pdf_worker.terminate)
        self.pdf_worker.start()
