from pathlib import Path
from datetime import datetime
import random, re, sys
sys.path.insert(0, 'D:/Coding/pyton_pro')
from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer

data_path = Path(r'D:\Coding\pyton_pro\test_data\cascade_extracted')
sensor_id = 2
filter_type = 'HIGH'

pattern = f'*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2'
rd2_files = list(data_path.glob(pattern))
print(f'Found files: {len(rd2_files)}')

dates = set()
for f in rd2_files:
    m = re.search(r'SMP_(\d{8})', f.name)
    if m: dates.add(m.group(1))
all_dates = sorted(list(dates))
print(f'All dates: {len(all_dates)}')

selected = random.sample(all_dates, 4)
selected.sort()
print(f'Selected: {selected}')

spectra_data = {}
analyzer = VibrationAnalyzer()
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
        if values:
            freq, amp = analyzer.calculate_spectrum(values, fs)
            if len(freq) > 0 and len(amp) > 0:
                spectra_data[dt.strftime('%d.%m.%Y')] = list(zip(freq, amp))
                print(f'OK: {date_str}')
    except Exception as e:
        print(f'ERROR {date_str}: {e}')

print(f'\nFinal: {len(spectra_data)} spectra')
