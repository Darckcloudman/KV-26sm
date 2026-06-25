with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Обновляем переменные для 3 пиков
content = content.replace(
    'self.peak_points = []\n        self.peak_line = None',
    'self.peak_points = []\n        self.peak_lines = []\n        self.peak_bands = [(0, 50), (50, 500), (500, 5000)]  # Low, Medium, High Hz'
)

content = content.replace(
    'self.show_peaks = False',
    'self.show_peaks = False\n        self.peak_data = {}  # {date: [(freq1,amp1), (freq2,amp2), (freq3,amp3)]}'
)

# Обновляем _draw_lines для 3 пиков по диапазонам
old_draw = """def _draw_lines(self):
        colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        for line in self.lines: line.remove()
        for pt in self.peak_points: pt.remove()
        if self.peak_line: self.peak_line.remove()
        self.lines = []
        self.peak_points = []
        self.peak_line = None
        dates_sorted = sorted(self.spectra_data.keys())
        peak_freqs, peak_amps, peak_ys = [], [], []
        for i, date in enumerate(dates_sorted):
            pts = self.spectra_data[date]
            freq = np.array([p[0] for p in pts])
            amp = np.array([p[1] for p in pts])
            zone = self._get_zone(np.max(amp))
            line, = self.ax.plot(freq, [i]*len(freq), amp, color=colors[zone], linewidth=1.2, label=f'{date} ({zone})', alpha=0.9)
            self.lines.append(line)
            max_idx = np.argmax(amp)
            peak_freq, peak_amp = freq[max_idx], amp[max_idx]
            peak_ys.append(i); peak_freqs.append(peak_freq); peak_amps.append(peak_amp)
            pt = self.ax.scatter([peak_freq], [i], [peak_amp], color='red', s=20, depthshade=True, zorder=10)
            self.peak_points.append(pt)
        if self.show_peaks and len(peak_freqs) > 1:
            self.peak_line, = self.ax.plot(peak_freqs, peak_ys, peak_amps, color='red', linestyle='--', linewidth=2, label='Critical peaks', alpha=0.8)"""

new_draw = """def _draw_lines(self):
        colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        for line in self.lines: line.remove()
        for pt in self.peak_points: pt.remove()
        for pl in self.peak_lines: pl.remove()
        self.lines = []
        self.peak_points = []
        self.peak_lines = []
        self.peak_data = {}
        # Сортировка дат по хронологии
        from datetime import datetime
        dates_dt = [(d, datetime.strptime(d, '%d.%m.%Y')) for d in self.spectra_data.keys()]
        dates_dt.sort(key=lambda x: x[1])
        dates_sorted = [d[0] for d in dates_dt]
        
        # 3 диапазона частот для пиков
        peak_bands = [(0, 50, 'Low'), (50, 500, 'Med'), (500, 5000, 'High')]
        band_colors = ['#FF0000', '#00FF00', '#0000FF']
        
        for i, date in enumerate(dates_sorted):
            pts = self.spectra_data[date]
            freq = np.array([p[0] for p in pts])
            amp = np.array([p[1] for p in pts])
            zone = self._get_zone(np.max(amp))
            line, = self.ax.plot(freq, [i]*len(freq), amp, color=colors[zone], linewidth=1.2, label=f'{date} ({zone})', alpha=0.9)
            self.lines.append(line)
            self.peak_data[date] = []
            # 3 пика по диапазонам
            for f_min, f_max, _ in peak_bands:
                mask = (freq >= f_min) & (freq < f_max)
                if np.any(mask):
                    sub_freq = freq[mask]
                    sub_amp = amp[mask]
                    max_idx = np.argmax(sub_amp)
                    peak_freq = sub_freq[max_idx]
                    peak_amp = sub_amp[max_idx]
                    self.peak_data[date].append((peak_freq, peak_amp))
                    pt = self.ax.scatter([peak_freq], [i], [peak_amp], color='red', s=15, depthshade=True, zorder=10)
                    self.peak_points.append(pt)
        
        # Пунктирные линии для каждого диапазона
        if self.show_peaks and len(dates_sorted) > 1:
            for band_idx, (f_min, f_max, band_name) in enumerate(peak_bands):
                line_freqs, line_amps, line_ys = [], [], []
                for i, date in enumerate(dates_sorted):
                    if date in self.peak_data and len(self.peak_data[date]) > band_idx:
                        pf, pa = self.peak_data[date][band_idx]
                        line_freqs.append(pf)
                        line_amps.append(pa)
                        line_ys.append(i)
                if len(line_freqs) > 1:
                    pl, = self.ax.plot(line_freqs, line_ys, line_amps, color=band_colors[band_idx], 
                                       linestyle='--', linewidth=2, label=f'{band_name} trend', alpha=0.7)
                    self.peak_lines.append(pl)"""

content = content.replace(old_draw, new_draw)

# Обновляем legend
content = content.replace(
    "self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=9)",
    "self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=8)"
)

with open('D:/Coding/pyton_pro/test_cascade_v19.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('v1.9 created')
