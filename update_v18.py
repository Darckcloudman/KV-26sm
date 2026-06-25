with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Обновляем _draw_lines
old_draw = """def _draw_lines(self):
        colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        for line in self.lines: line.remove()
        self.lines = []
        for i, date in enumerate(sorted(self.spectra_data.keys())):
            pts = self.spectra_data[date]
            freq = np.array([p[0] for p in pts])
            amp = np.array([p[1] for p in pts])
            zone = self._get_zone(np.max(amp))
            line, = self.ax.plot(freq, [i]*len(freq), amp, color=colors[zone], linewidth=1.2, label=f'{date} ({zone})', alpha=0.9)
            self.lines.append(line)"""

new_draw = """def _draw_lines(self):
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

content = content.replace(old_draw, new_draw)

# labelpad
content = content.replace(
    "self.ax.set_ylabel('Records (by date)', fontsize=12, fontweight='bold')",
    "self.ax.set_ylabel('Records (by date)', fontsize=12, fontweight='bold', labelpad=12)")

# Кнопка peaks
old_btn = """plt.figtext(0.55, 0.96, 'Show:', fontsize=11, fontweight='bold')
    
    def _sensor_click"""

new_btn = """plt.figtext(0.55, 0.96, 'Show:', fontsize=11, fontweight='bold')
        ax_peaks = plt.axes([0.70, 0.92, 0.12, btn_h])
        peaks_col = '#FF5722' if self.show_peaks else '#2196F3'
        peaks_lbl = 'Hide peaks' if self.show_peaks else 'Show peaks'
        self.peaks_btn = Button(ax_peaks, peaks_lbl, color=peaks_col, hovercolor='#64B5F6')
        self.peaks_btn.label.set_color('white')
        self.peaks_btn.label.set_weight('bold')
        self.peaks_btn.on_clicked(self._peaks_click)
        plt.figtext(0.70, 0.96, 'Peaks:', fontsize=11, fontweight='bold')
    
    def _peaks_click(self, e):
        if self.is_loading: return
        self.show_peaks = not self.show_peaks
        self.peaks_btn.color = '#FF5722' if self.show_peaks else '#2196F3'
        self.peaks_btn.label.set_text('Hide peaks' if self.show_peaks else 'Show peaks')
        self._draw_lines()
        self._setup_axes()
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()
    
    def _sensor_click"""

content = content.replace(old_btn, new_btn)

with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('v1.8 complete')
