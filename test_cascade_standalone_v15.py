# -*- coding: utf-8 -*-
"""
Тестовый модуль для построения каскадного графика спектров (3D)
Использует данные из D:\Coding\pyton_pro\test_data\cascade_extracted

Запуск: python test_cascade_standalone.py

v1.5: Оптимизация - обновление данных без пересоздания графика
"""

import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import re
import time

# Добавляем путь к проекту для импорта парсеров
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer


class CascadeSpectrumViewer:
    """Просмотрщик каскадных спектров с GUI (оптимизированный)."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.spectra_data = {}
        self.all_dates = []
        self.analyzer = VibrationAnalyzer()
        self.current_sensor = 2
        self.show_7_spectra = False
        self.fig = None
        self.ax = None
        self.toggle_button = None
        self.buttons = []
        self.lines = []
        self.is_loading = False
    
    def load_spectra(self, sensor_id: int = 2, filter_type: str = "HIGH", show_7: bool = False):
        """Загрузить спектры для датчика и типа фильтра."""
        self.is_loading = True
        
        print(f"\n{'='*70}")
        print(f"ЗАГРУЗКА СПЕКТРОВ")
        print(f"{'='*70}")
        print(f"Датчик: {sensor_id}")
        print(f"Фильтр: {filter_type}")
        print(f"Показать: {'7' if show_7 else '4'} графика")
        print()
        
        pattern = f"*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2"
        rd2_files = list(self.data_path.glob(pattern))
        
        print(f"Поиск: {pattern}")
        print(f"Найдено файлов: {len(rd2_files)}")
        
        # Извлекаем даты
        dates_found = set()
        for f in rd2_files:
            match = re.search(r'SMP_(\d{8})', f.name)
            if match:
                dates_found.add(match.group(1))
        
        self.all_dates = sorted(list(dates_found))
        print(f"Дат: {len(self.all_dates)}")
        
        if not self.all_dates:
            print("\n[ERROR] Нет данных!")
            self.is_loading = False
            return False
        
        # Выбираем даты
        selected_dates = self.all_dates[:7] if show_7 else self.all_dates[:4]
        print(f"Выбрано дат: {len(selected_dates)}\n")
        
        # Загружаем спектры
        self.spectra_data = {}
        
        for date_str in selected_dates:
            matching_files = [f for f in rd2_files if date_str in f.name]
            
            if not matching_files:
                continue
            
            file_path = matching_files[0]
            
            try:
                parser = RD2Parser(str(file_path))
                result = parser.parse()
                
                if not result or 'values' not in result:
                    continue
                
                dt = datetime.strptime(date_str, "%Y%m%d")
                date_formatted = dt.strftime("%d.%m.%Y")
                
                values = result['values']
                sampling_freq = result['metadata'].get('sampling_frequency', 25600)
                
                if len(values) == 0:
                    continue
                
                frequencies, amplitudes = self.analyzer.calculate_spectrum(values, sampling_freq)
                
                if len(frequencies) and len(amplitudes):
                    self.spectra_data[date_formatted] = list(zip(frequencies, amplitudes))
                    
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
        
        print(f"\n{'='*70}")
        print(f"ЗАГРУЖЕНО: {len(self.spectra_data)} спектров")
        print(f"{'='*70}\n")
        
        self.is_loading = False
        return len(self.spectra_data) > 0
    
    def plot_cascade(self, title: str = "Каскад спектров"):
        """Построить начальный график."""
        if not self.spectra_data:
            print("[ERROR] Нет данных")
            return
        
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.subplots_adjust(top=0.88, right=0.75)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Рисуем линии
        self._draw_lines()
        
        # Настройка осей
        self._setup_axes()
        
        # Добавляем кнопки
        self._add_controls()
        
        # Сохраняем
        output_path = Path(__file__).parent / "cascade_spectrum.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"График сохранён: {output_path}")
        
        plt.show()
    
    def _draw_lines(self):
        """Нарисовать все линии спектров."""
        iso_colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        
        # Очищаем старые линии
        for line in self.lines:
            line.remove()
        self.lines = []
        
        sorted_dates = sorted(self.spectra_data.keys())
        
        for i, date_str in enumerate(sorted_dates):
            spectrum_points = self.spectra_data[date_str]
            frequencies = np.array([p[0] for p in spectrum_points])
            amplitudes = np.array([p[1] for p in spectrum_points])
            
            max_amp = np.max(amplitudes)
            zone = self._get_iso_zone(max_amp)
            color = iso_colors[zone]
            
            line, = self.ax.plot(frequencies, [i] * len(frequencies), amplitudes,
                               color=color, linewidth=1.2, label=f"{date_str} (Зона {zone})", alpha=0.9)
            self.lines.append(line)
    
    def _setup_axes(self):
        """Настроить оси графика."""
        sorted_dates = sorted(self.spectra_data.keys())
        n = len(sorted_dates)
        
        self.ax.set_xlabel('Частота (Гц)', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Записи (по датам)', fontsize=12, fontweight='bold')
        self.ax.set_zlabel('Амплитуда', fontsize=12, fontweight='bold')
        
        self.ax.set_yticks(range(n))
        self.ax.set_yticklabels(sorted_dates, fontsize=10)
        self.ax.view_init(elev=25, azim=-60)
        self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=9)
        self.ax.grid(True, alpha=0.3)
    
    def _add_controls(self):
        """Добавить кнопки управления."""
        from matplotlib.widgets import Button
        
        btn_width = 0.04
        btn_height = 0.035
        start_y = 0.92
        
        # Кнопки датчиков 1-8
        for sensor_id in range(1, 9):
            x_pos = 0.08 + (sensor_id - 1) * 0.05
            ax_btn = plt.axes([x_pos, start_y, btn_width, btn_height])
            
            color = '#4CAF50' if sensor_id == self.current_sensor else '#E0E0E0'
            text_color = 'white' if sensor_id == self.current_sensor else 'black'
            
            btn = Button(ax_btn, f'{sensor_id}', color=color, hovercolor='#8BC34A')
            btn.label.set_color(text_color)
            btn.label.set_weight('bold')
            btn.on_clicked(lambda event, sid=sensor_id: self._on_sensor_click(sid))
            self.buttons.append(btn)
        
        plt.figtext(0.02, 0.96, 'Датчик:', fontsize=11, fontweight='bold')
        
        # Тумблер 4/7
        ax_toggle = plt.axes([0.55, start_y, 0.12, btn_height])
        toggle_label = '7 графиков' if self.show_7_spectra else '4 графика'
        toggle_color = '#FF5722' if self.show_7_spectra else '#4CAF50'
        
        self.toggle_button = Button(ax_toggle, toggle_label, color=toggle_color, hovercolor='#FF8A65')
        self.toggle_button.label.set_color('white')
        self.toggle_button.label.set_weight('bold')
        self.toggle_button.on_clicked(self._on_toggle_click)
        
        plt.figtext(0.55, 0.96, 'Показать:', fontsize=11, fontweight='bold')
    
    def _on_sensor_click(self, sensor_id: int):
        """Клик по кнопке датчика - обновление без пересоздания."""
        if self.is_loading:
            print("[WAIT] Загрузка...")
            return
        
        print(f"\nДатчик: {sensor_id}")
        self.current_sensor = sensor_id
        
        # Обновляем кнопки визуально
        for i, btn in enumerate(self.buttons):
            sid = i + 1
            btn.color = '#4CAF50' if sid == sensor_id else '#E0E0E0'
            btn.label.set_color('white' if sid == sensor_id else 'black')
        
        # Загружаем данные
        loaded = self.load_spectra(sensor_id=sensor_id, filter_type="HIGH", show_7=self.show_7_spectra)
        
        if loaded:
            # Обновляем линии и оси
            self._draw_lines()
            self._setup_axes()
            
            # Обновляем заголовок
            n = len(self.spectra_data)
            self.fig.suptitle(f"ВЭУ 37 - Датчик {sensor_id} (HIGH)\nКаскад спектров за {n} записей",
                            fontsize=16, fontweight='bold')
            
            # Перерисовка
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
            
            # Сохраняем
            output_path = Path(__file__).parent / "cascade_spectrum.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            
            print(f"  [OK] Обновлён")
        else:
            print(f"[ERROR] Нет данных")
            # Возвращаем кнопку
            self.buttons[sensor_id-1].color = '#E0E0E0'
            self.buttons[sensor_id-1].label.set_color('black')
    
    def _on_toggle_click(self, event):
        """Клик по тумблеру 4/7."""
        if self.is_loading:
            print("[WAIT] Загрузка...")
            return
        
        self.show_7_spectra = not self.show_7_spectra
        n = 7 if self.show_7_spectra else 4
        
        print(f"\nПоказать: {n} графиков")
        
        # Обновляем тумблер
        self.toggle_button.color = '#FF5722' if self.show_7_spectra else '#4CAF50'
        self.toggle_button.label.set_text('7 графиков' if self.show_7_spectra else '4 графика')
        
        # Загружаем данные
        loaded = self.load_spectra(sensor_id=self.current_sensor, filter_type="HIGH", show_7=self.show_7_spectra)
        
        if loaded:
            self._draw_lines()
            self._setup_axes()
            
            n = len(self.spectra_data)
            self.fig.suptitle(f"ВЭУ 37 - Датчик {self.current_sensor} (HIGH)\nКаскад спектров за {n} записей",
                            fontsize=16, fontweight='bold')
            
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
            
            output_path = Path(__file__).parent / "cascade_spectrum.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            
            print(f"  [OK] Обновлён")
        else:
            # Возвращаем обратно
            self.show_7_spectra = not self.show_7_spectra
            print("[ERROR] Нет данных")
    
    def _get_iso_zone(self, rms_value: float) -> str:
        """Определить зону по ISO 10816."""
        normalized = rms_value * 10
        if normalized < 2.3: return 'A'
        elif normalized < 4.5: return 'B'
        elif normalized < 7.8: return 'C'
        else: return 'D'


def main():
    """Основная функция."""
    print("="*70)
    print("CASCADE SPECTRUM VIEWER v1.5")
    print("Оптимизированный (без пересоздания графика)")
    print("="*70)
    
    data_path = Path(r"D:\Coding\pyton_pro\test_data\cascade_extracted")
    
    if not data_path.exists():
        print(f"\n[ERROR] Папка не найдена: {data_path}")
        input("\nНажмите Enter...")
        return
    
    viewer = CascadeSpectrumViewer(data_path)
    
    # Загружаем начальные данные
    loaded = viewer.load_spectra(sensor_id=2, filter_type="HIGH", show_7=False)
    
    if not loaded:
        print("\n[ERROR] Не удалось загрузить")
        input("\nНажмите Enter...")
        return
    
    # Строим график
    title = f"ВЭУ 37 - Датчик 2 (HIGH)\nКаскад спектров за {len(viewer.spectra_data)} записей"
    viewer.plot_cascade(title=title)
    
    print("\n" + "="*70)
    print("ГОТОВО")
    print("="*70)
    print("\nУправление:")
    print("  1-8: Выбор датчика")
    print("  4/7: Переключатель количества графиков")
    print("\n[INFO] Графики обновляются без пересоздания окна")
    input("\nНажмите Enter...")


if __name__ == "__main__":
    main()
