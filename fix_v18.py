with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Исправляем сортировку дат - используем datetime
old_sort = """dates_sorted = sorted(self.spectra_data.keys())"""
new_sort = """dates_sorted = sorted(self.spectra_data.keys(), key=lambda d: datetime.strptime(d, '%d.%m.%Y'))"""
content = content.replace(old_sort, new_sort)

# 2. Исправляем логику пиков - ищем в диапазоне ±100Hz от первого пика
old_peaks = """dates_sorted = sorted(self.spectra_data.keys(), key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
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
            self.peak_points.append(pt)"""

new_peaks = """dates_sorted = sorted(self.spectra_data.keys(), key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
        peak_freqs, peak_amps, peak_ys = [], [], []
        ref_freq = None  # Опорная частота первого пика
        for i, date in enumerate(dates_sorted):
            pts = self.spectra_data[date]
            freq = np.array([p[0] for p in pts])
            amp = np.array([p[1] for p in pts])
            zone = self._get_zone(np.max(amp))
            line, = self.ax.plot(freq, [i]*len(freq), amp, color=colors[zone], linewidth=1.2, label=f'{date} ({zone})', alpha=0.9)
            self.lines.append(line)
            # Поиск пика в диапазоне ±100Hz от опорного
            if ref_freq is None:
                # Первый спектр - глобальный максимум
                max_idx = np.argmax(amp)
                ref_freq = freq[max_idx]
            else:
                # Остальные - максимум в диапазоне ±100Hz
                mask = (freq >= ref_freq - 100) & (freq <= ref_freq + 100)
                if np.any(mask):
                    max_idx = np.argmax(amp[mask])
                    max_idx = np.where(mask)[0][max_idx]
                else:
                    max_idx = np.argmax(amp)
            peak_freq, peak_amp = freq[max_idx], amp[max_idx]
            peak_ys.append(i); peak_freqs.append(peak_freq); peak_amps.append(peak_amp)
            pt = self.ax.scatter([peak_freq], [i], [peak_amp], color='red', s=20, depthshade=True, zorder=10)
            self.peak_points.append(pt)"""

content = content.replace(old_peaks, new_peaks)

with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('v1.8 updated - dates sorted + peaks in ±100Hz range')
