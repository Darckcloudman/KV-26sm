with open('D:/Coding/pyton_pro/test_cascade_v19.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Обновляем заголовок
content = content.replace('CASCADE SPECTRUM v1.8', 'CASCADE SPECTRUM v1.9 - 3 Band Peaks')
content = content.replace('4/7 = Dates, Peaks = Critical points', '4/7 = Dates, Peaks = 3 bands (Low/Med/High)')

# Обновляем кнопку peaks
content = content.replace(
    "peaks_lbl = 'Hide peaks' if self.show_peaks else 'Show peaks'",
    "peaks_lbl = 'Hide trends' if self.show_peaks else 'Show trends'"
)
content = content.replace(
    "self.peaks_btn.label.set_text('Hide peaks' if self.show_peaks else 'Show peaks')",
    "self.peaks_btn.label.set_text('Hide trends' if self.show_peaks else 'Show trends')"
)

with open('D:/Coding/pyton_pro/test_cascade_v19.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('v1.9 updated')
