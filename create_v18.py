with open('D:/Coding/pyton_pro/test_cascade_v17.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('self.toggle_btn = None', 
    'self.toggle_btn = None\n        self.peaks_btn = None\n        self.show_peaks = False\n        self.peak_points = []\n        self.peak_line = None')

content = content.replace('CASCADE SPECTRUM v1.7', 'CASCADE SPECTRUM v1.8')
content = content.replace('4/7 = Random dates', '4/7 = Dates, Peaks = Critical points')

with open('D:/Coding/pyton_pro/test_cascade_v18.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Base created')
