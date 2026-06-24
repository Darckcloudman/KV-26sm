import random
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
        self.spectra_data = {}  # {date: [(freq, amp), ...]}
        self.all_dates = []  # Все доступные даты
        self.analyzer = VibrationAnalyzer()
        self.current_sensor = 2  # Датчик по умолчанию
        self.show_7_spectra = False  # False=4 графика, True=7 графиков
        self.fig = None
        self.ax = None
        self.toggle_button = None
        self.lines = []  # Хранение линий графиков для обновления
        self.is_loading = False  # Флаг загрузки
    
    def load_spectra(self, sensor_id: int = 2, filter_type: str = "HIGH", show_7: bool = False):
        """
        Загрузить спектры для датчика и типа фильтра.
        
        Args:
            sensor_id: Номер датчика (1-8)
            filter_type: Тип фильтра (FILTER, LOW, HIGH)
            show_7: Показать 7 графиков (False = 4 графика)
        """
        print(f"\n{'='*70}")
        print(f"ЗАГРУЗКА СПЕКТРОВ")
        print(f"{'='*70}")
        print(f"Датчик: {sensor_id}")
        print(f"Фильтр: {filter_type}")
        print(f"Показать: {'7' if show_7 else '4'} графика")
        print(f"Путь: {self.data_path}")
        print()
        
        # Ищем все файлы для выбранного датчика и фильтра
        pattern = f"*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2"
        rd2_files = list(self.data_path.glob(pattern))
        
        print(f"Поиск по маске: {pattern}")
        print(f"Всего найдено файлов: {len(rd2_files)}")
        
        # Извлекаем все уникальные даты
        import re
        dates_found = set()
        for f in rd2_files:
            match = re.search(r'SMP_(\d{8})', f.name)
            if match:
                date_str = match.group(1)
                dates_found.add(date_str)
        
        self.all_dates = sorted(list(dates_found))
        print(f"Найдено дат: {len(self.all_dates)}")
        
        if not self.all_dates:
            print(f"\n[ERROR] Нет данных!")
            return False
        
        # Выбираем даты
        if show_7:
            # Все 7 дат
            selected_dates = random.sample(self.all_dates, 7)
        else:
            # Первые 4 даты (по возрастанию)
            selected_dates = random.sample(self.all_dates, 4)
        
        print(f"Выбрано дат: {len(selected_dates)}")
        for d in selected_dates:
            print(f"  - {d}")
        print()
        
        # Загружаем файлы для выбранных дат
        self.spectra_data = {}
        
        for date_str in selected_dates:
            # Ищем файл для этой даты
            matching_files = [f for f in rd2_files if date_str in f.name]
            
            if not matching_files:
                print(f"  [SKIP] Нет файла для {date_str}")
                continue
            
            file_path = matching_files[0]
            print(f"Обработка: {file_path.name}")
            
            try:
                # Парсим файл
                parser = RD2Parser(str(file_path))
                result = parser.parse()
                
                if not result or 'values' not in result or 'metadata' not in result:
                    print(f"  [SKIP] Нет данных в файле")
                    continue
                
                # Извлекаем дату в красивом формате
                dt = datetime.strptime(date_str, "%Y%m%d")
                date_formatted = dt.strftime("%d.%m.%Y")
                
                # Получаем спектр через FFT
                values = result['values']
                sampling_freq = result['metadata'].get('sampling_frequency', 25600)
                
                if len(values) == 0:
                    print(f"  [SKIP] Пустые данные")
                    continue
                
                frequencies, amplitudes = self.analyzer.calculate_spectrum(values, sampling_freq)
                
                if not len(frequencies) or not len(amplitudes):
                    print(f"  [SKIP] Пустой спектр")
                    continue
                
                # Сохраняем данные
                self.spectra_data[date_formatted] = list(zip(frequencies, amplitudes))
                print(f"  [OK] {len(frequencies)} точек, дата: {date_formatted}")
                
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        print(f"\n{'='*70}")
        print(f"ЗАГРУЖЕНО СПЕКТРОВ: {len(self.spectra_data)}")
        print(f"{'='*70}\n")
        
        return len(self.spectra_data) > 0
    
    def plot_cascade(self, title: str = "Каскад спектров"):
        """
        Построить каскадный график с кнопками выбора датчика и тумблером 4/7.
        
        Args:
            title: Заголовок графика
        """
        if not self.spectra_data:
            print("[ERROR] Нет данных для отображения")
            return
        
        print("Построение каскадного графика...")
        
        # Создаём фигуру
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Добавляем место для кнопок сверху
        plt.subplots_adjust(top=0.88)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Цвета по ISO 10816 (зонам тревожности)
        iso_colors = {
            'A': '#2E7D32',  # Зелёный
            'B': '#F9A825',  # Жёлтый
            'C': '#EF6C00',  # Оранжевый
            'D': '#C62828',  # Красный
        }
        
        # Сортируем даты
        sorted_dates = sorted(self.spectra_data.keys())
        n_spectra = len(sorted_dates)
        
        # Рисуем каждый спектр (толщина 1.2 - на 40% меньше)
        for i, date_str in enumerate(sorted_dates):
            spectrum_points = self.spectra_data[date_str]
            frequencies = np.array([p[0] for p in spectrum_points])
            amplitudes = np.array([p[1] for p in spectrum_points])
            
            # Y-координата (смещение для каскада)
            y_pos = i
            
            # Определяем цвет по максимальному уровню вибрации
            max_amp = np.max(amplitudes)
            zone = self._get_iso_zone(max_amp)
            color = iso_colors[zone]
            
            # Рисуем линию спектра
            self.ax.plot(frequencies, [y_pos] * len(frequencies), amplitudes, 
                   color=color, linewidth=1.2, label=f"{date_str} (Зона {zone})", alpha=0.9)
        
        # Настройка осей
        self.ax.set_xlabel('Частота (Гц)', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Записи (по датам)', fontsize=12, fontweight='bold')
        self.ax.set_zlabel('Амплитуда', fontsize=12, fontweight='bold')
        
        # Устанавливаем метки дат на оси Y
        self.ax.set_yticks(range(n_spectra))
        self.ax.set_yticklabels(sorted_dates, fontsize=10)
        
        # Поворот для лучшего обзора
        self.ax.view_init(elev=25, azim=-60)
        
        # Легенда
        legend = self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1))
        plt.setp(legend.get_texts(), fontsize=9)
        
        # Сетка
        self.ax.grid(True, alpha=0.3)
        
        # Добавляем кнопки
        self._add_controls()
        
        # Сохраняем
        output_path = Path(__file__).parent / "cascade_spectrum.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"График сохранён: {output_path}")
        
        plt.show()
        print("Готово!")

    def _add_controls(self):
        """Добавить кнопки датчиков 1-8 и тумблер 4/7."""
        from matplotlib.widgets import Button
        
        # Кнопки датчиков
        btn_width = 0.04
        btn_height = 0.035
        start_x = 0.08
        start_y = 0.92
        
        self.buttons = []
        
        for sensor_id in range(1, 9):
            x_pos = start_x + (sensor_id - 1) * (btn_width + 0.01)
            ax_btn = plt.axes([x_pos, start_y, btn_width, btn_height])
            color = '#4CAF50' if sensor_id == self.current_sensor else '#E0E0E0'
            text_color = 'white' if sensor_id == self.current_sensor else 'black'
            
            btn = Button(ax_btn, f'{sensor_id}', color=color, hovercolor='#8BC34A')
            btn.label.set_color(text_color)
            btn.label.set_weight('bold')
            btn.on_clicked(lambda event, sid=sensor_id: self._on_sensor_click(sid))
            self.buttons.append(btn)
        
        plt.figtext(0.02, 0.96, 'Датчик:', fontsize=11, fontweight='bold')
        
        # Тумблер 4/7 графиков
        toggle_x = 0.55
        toggle_w = 0.12
        ax_toggle = plt.axes([toggle_x, start_y, toggle_w, btn_height])
        
        toggle_label = '7 графиков' if self.show_7_spectra else '4 графика'
        toggle_color = '#FF5722' if self.show_7_spectra else '#4CAF50'
        
        self.toggle_button = Button(ax_toggle, toggle_label, color=toggle_color, hovercolor='#FF8A65')
        self.toggle_button.label.set_color('white')
        self.toggle_button.label.set_weight('bold')
        self.toggle_button.on_clicked(self._on_toggle_click)
        
        plt.figtext(0.55, 0.96, 'Показать:', fontsize=11, fontweight='bold')
    
    def _on_toggle_click(self, event):
        """Обработчик клика по тумблеру 4/7."""
        # Переключаем режим
        self.show_7_spectra = not self.show_7_spectra
        
        print(f"\nПереключено на: {'7' if self.show_7_spectra else '4'} графиков")
        
        # Закрываем текущий график
        plt.close(self.fig)
        
        # Загружаем данные с новым количеством
        loaded = self.load_spectra(sensor_id=self.current_sensor, filter_type="HIGH", show_7=self.show_7_spectra)
        
        if loaded:
            n = len(self.spectra_data)
            title = f"ВЭУ 37 - Датчик {self.current_sensor} (HIGH)\nКаскад спектров за {n} записей"
            self.plot_cascade(title=title)
        else:
            print(f"[ERROR] Нет данных")
    
    def _on_sensor_click(self, sensor_id: int):
        """Обработчик клика по кнопке датчика."""
        print(f"\nВыбран датчик: {sensor_id}")
        
        # Обновляем текущий датчик
        self.current_sensor = sensor_id
        
        # Закрываем текущий график
        plt.close(self.fig)
        
        # Загружаем данные для нового датчика
        loaded = self.load_spectra(sensor_id=sensor_id, filter_type="HIGH", date_set_index=self.current_date_set)
        
        if loaded:
            # Строим новый график
            title = f"ВЭУ 37 - Датчик {sensor_id} (HIGH)\nКаскад спектров за {len(self.spectra_data)} записей"
            self.plot_cascade(title=title)
        else:
            print(f"[ERROR] Нет данных для датчика {sensor_id}")

    def _get_iso_zone(self, rms_value: float) -> str:
        """
        Определение зоны состояния по ISO 10816-21:2015 / ГОСТ 10816-21:2021

        Для виброскорости (мм/с):
        - Zone A: < 2.3 мм/с (Хорошо) - Зелёный
        - Zone B: 2.3 - 4.5 мм/с (Внимание) - Жёлтый
        - Zone C: 4.5 - 7.8 мм/с (Тревога) - Оранжевый
        - Zone D: > 7.8 мм/с (Критично) - Красный
        
        Args:
            rms_value: значение СКЗ виброскорости (или макс. амплитуда для спектра)
        
        Returns:
            'A', 'B', 'C' или 'D'
        """
        # Нормализуем амплитуду к примерным значениям виброскорости
        # (для спектра используем относительные значения)
        normalized_value = rms_value * 10  # Масштабируем для наглядности
        
        if normalized_value < 2.3:
            return 'A'
        elif normalized_value < 4.5:
            return 'B'
        elif normalized_value < 7.8:
            return 'C'
        else:
            return 'D'


def main():
    """Основная функция."""
    print("="*70)
    print("CASCADE SPECTRUM VIEWER v1.4")
    print("Тестирование каскадного графика спектров")
    print("="*70)
    
    # Путь к данным
    data_path = Path(r"D:\Coding\pyton_pro\test_data\cascade_extracted")
    
    if not data_path.exists():
        print(f"\n[ERROR] Папка не найдена: {data_path}")
        print("\nРаспакуйте архивы:")
        print("  python extract_all_archives.py")
        input("\nНажмите Enter для выхода...")
        return
    
    # Создаём просмотрщик
    viewer = CascadeSpectrumViewer(data_path)
    
    # Загружаем спектры (датчик 2, HIGH фильтр, 4 графика)
    sensor_id = 2
    filter_type = "HIGH"
    show_7 = False  # По умолчанию 4 графика
    
    loaded = viewer.load_spectra(sensor_id=sensor_id, filter_type=filter_type, show_7=show_7)
    
    if not loaded:
        print("\n[ERROR] Не удалось загрузить спектры")
        input("\nНажмите Enter для выхода...")
        return
    
    # Строим график с кнопками
    title = f"ВЭУ 37 - Датчик {sensor_id} (HIGH)\nКаскад спектров за {len(viewer.spectra_data)} записей"
    viewer.plot_cascade(title=title)
    
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*70)
    print("\nКнопки:")
    print("  1-8: Выбор датчика")
    print("  4 графика/7 графиков: Переключатель количества")
    input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()
