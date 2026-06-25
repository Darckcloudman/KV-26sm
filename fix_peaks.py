with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем _draw_lines - добавляем проверку на None для peak_line
old_clear = """for line in self.lines: line.remove()
        for pt in self.peak_points: pt.remove()
        if self.peak_line: self.peak_line.remove()
        self.lines = []
        self.peak_points = []
        self.peak_line = None"""

new_clear = """for line in self.lines:
            try: line.remove()
            except: pass
        for pt in self.peak_points:
            try: pt.remove()
            except: pass
        if self.peak_line:
            try: self.peak_line.remove()
            except: pass
        self.lines = []
        self.peak_points = []
        self.peak_line = None"""

content = content.replace(old_clear, new_clear)

# Исправляем _sensor_click - сбрасываем show_peaks
old_sensor = """def _sensor_click(self, sid):
        if self.is_loading: return
        print(f'Sensor: {sid}')
        self.current_sensor = sid"""

new_sensor = """def _sensor_click(self, sid):
        if self.is_loading: return
        print(f'Sensor: {sid}')
        self.current_sensor = sid
        # Сброс пиков при смене датчика
        self.show_peaks = False
        if self.peaks_btn:
            self.peaks_btn.color = '#2196F3'
            self.peaks_btn.label.set_text('Show peaks')"""

content = content.replace(old_sensor, new_sensor)

# Исправляем _toggle_click - та же очистка
old_toggle_clear = """if self.load_spectra(self.current_sensor, 'HIGH'):
            self._draw_lines()
            self._setup_axes()
            self.fig.suptitle(f'Sensor {self.current_sensor} (HIGH) - {len(self.spectra_data)} records', fontsize=16, fontweight='bold')
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
    
    def _get_zone"""

new_toggle_clear = """if self.load_spectra(self.current_sensor, 'HIGH'):
            self._draw_lines()
            self._setup_axes()
            self.fig.suptitle(f'Sensor {self.current_sensor} (HIGH) - {len(self.spectra_data)} records', fontsize=16, fontweight='bold')
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
    
    def _peaks_click"""

content = content.replace(old_toggle_clear, new_toggle_clear)

with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed: peak lines cleared on sensor change')
