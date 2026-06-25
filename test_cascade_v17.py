# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use('TkAgg')
import sys, random
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import re

sys.path.insert(0, str(Path(__file__).parent))
from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer

class CascadeSpectrumViewer:
    def __init__(self, data_path):
        self.data_path = Path(data_path)
        self.spectra_data = {}
        self.all_dates = []
        self.analyzer = VibrationAnalyzer()
        self.current_sensor = 2
        self.show_7 = False
        self.fig = None
        self.ax = None
        self.buttons = []
        self.lines = []
        self.is_loading = False
        self.toggle_btn = None
    
    def load_spectra(self, sensor_id=2, filter_type='HIGH'):
        self.is_loading = True
        print(f'Data: sensor {sensor_id}, {filter_type}')
        pattern = f'*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2'
        rd2_files = list(self.data_path.glob(pattern))
        dates = set()
        for f in rd2_files:
            m = re.search(r'SMP_(\d{8})', f.name)
            if m: dates.add(m.group(1))
        self.all_dates = sorted(list(dates))
        if not self.all_dates:
            self.is_loading = False
            return False
        n = 7 if self.show_7 else 4
        selected = random.sample(self.all_dates, min(n, len(self.all_dates)))
        selected.sort()
        print(f'Dates ({len(selected)}): {selected}')
        self.spectra_data = {}
        for date_str in selected:
            files = [f for f in rd2_files if date_str in f.name]
            if not files: continue
            try:
                parser = RD2Parser(str(files[0]))
                res = parser.parse()
                if not res or 'values' not in res: continue
                dt = datetime.strptime(date_str, '%Y%m%d')
                values = res['values']
                fs = res['metadata'].get('sampling_frequency', 25600)
                if len(values) > 0:
                    freq, amp = self.analyzer.calculate_spectrum(values, fs)
                    if len(freq) > 0 and len(amp) > 0:
                        self.spectra_data[dt.strftime('%d.%m.%Y')] = list(zip(freq, amp))
            except: pass
        self.is_loading = False
        return len(self.spectra_data) > 0
    
    def plot_cascade(self, title):
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.subplots_adjust(top=0.88, right=0.75)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self._draw_lines()
        self._setup_axes()
        self._add_buttons()
        plt.savefig(Path(__file__).parent / 'cascade_spectrum.png', dpi=150, bbox_inches='tight')
        plt.show()
    
    def _draw_lines(self):
        colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        for line in self.lines: line.remove()
        self.lines = []
        for i, date in enumerate(sorted(self.spectra_data.keys())):
            pts = self.spectra_data[date]
            freq = np.array([p[0] for p in pts])
            amp = np.array([p[1] for p in pts])
            zone = self._get_zone(np.max(amp))
            line, = self.ax.plot(freq, [i]*len(freq), amp, color=colors[zone], linewidth=1.2, label=f'{date} ({zone})', alpha=0.9)
            self.lines.append(line)
    
    def _setup_axes(self):
        dates = sorted(self.spectra_data.keys())
        self.ax.set_xlabel('Frequency (Hz)', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Records (by date)', fontsize=12, fontweight='bold')
        self.ax.set_zlabel('Amplitude', fontsize=12, fontweight='bold')
        self.ax.set_yticks(range(len(dates)))
        self.ax.set_yticklabels(dates, fontsize=10)
        self.ax.view_init(elev=25, azim=-60)
        self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=9)
        self.ax.grid(True, alpha=0.3)
    
    def _add_buttons(self):
        btn_w, btn_h = 0.04, 0.035
        self.buttons = []
        for sid in range(1, 9):
            ax_btn = plt.axes([0.08+(sid-1)*0.05, 0.92, btn_w, btn_h])
            col = '#4CAF50' if sid==self.current_sensor else '#E0E0E0'
            btn = Button(ax_btn, f'{sid}', color=col, hovercolor='#8BC34A')
            btn.label.set_color('white' if sid==self.current_sensor else 'black')
            btn.label.set_weight('bold')
            btn.on_clicked(lambda e,s=sid: self._sensor_click(s))
            self.buttons.append(btn)
        plt.figtext(0.02, 0.96, 'Sensor:', fontsize=11, fontweight='bold')
        ax_tog = plt.axes([0.55, 0.92, 0.12, btn_h])
        tog_col = '#FF5722' if self.show_7 else '#4CAF50'
        tog_lbl = '7 graphs' if self.show_7 else '4 graphs'
        self.toggle_btn = Button(ax_tog, tog_lbl, color=tog_col, hovercolor='#FF8A65')
        self.toggle_btn.label.set_color('white')
        self.toggle_btn.label.set_weight('bold')
        self.toggle_btn.on_clicked(self._toggle_click)
        plt.figtext(0.55, 0.96, 'Show:', fontsize=11, fontweight='bold')
    
    def _sensor_click(self, sid):
        if self.is_loading: return
        print(f'Sensor: {sid}')
        self.current_sensor = sid
        for i,b in enumerate(self.buttons):
            b.color = '#4CAF50' if i+1==sid else '#E0E0E0'
            b.label.set_color('white' if i+1==sid else 'black')
        if self.load_spectra(sid, 'HIGH'):
            self._draw_lines()
            self._setup_axes()
            self.fig.suptitle(f'Sensor {sid} (HIGH) - {len(self.spectra_data)} records', fontsize=16, fontweight='bold')
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
    
    def _toggle_click(self, e):
        if self.is_loading: return
        self.show_7 = not self.show_7
        print(f'Show: {"7" if self.show_7 else "4"} random dates')
        self.toggle_btn.color = '#FF5722' if self.show_7 else '#4CAF50'
        self.toggle_btn.label.set_text('7 graphs' if self.show_7 else '4 graphs')
        if self.load_spectra(self.current_sensor, 'HIGH'):
            self._draw_lines()
            self._setup_axes()
            self.fig.suptitle(f'Sensor {self.current_sensor} (HIGH) - {len(self.spectra_data)} records', fontsize=16, fontweight='bold')
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
    
    def _get_zone(self, v):
        v = v*10
        return 'A' if v<2.3 else 'B' if v<4.5 else 'C' if v<7.8 else 'D'

def main():
    print('='*70+'\nCASCADE SPECTRUM v1.7\n'+'='*70)
    data_path = Path(r'D:\Coding\pyton_pro\test_data\cascade_extracted')
    if not data_path.exists():
        print('Folder not found!'); return
    viewer = CascadeSpectrumViewer(data_path)
    if viewer.load_spectra(2, 'HIGH'):
        viewer.plot_cascade(f'Sensor 2 (HIGH) - {len(viewer.spectra_data)} records')
        plt.show()
        print('Window closed')
    print('\nControls: 1-8 = Sensor, 4/7 = Random dates')

if __name__ == '__main__':
    main()




