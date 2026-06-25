from pathlib import Path
from datetime import datetime
import random, re, sys
sys.path.insert(0, 'D:/Coding/pyton_pro')
from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer
import traceback

data_path = Path(r'D:\Coding\pyton_pro\test_data\cascade_extracted')
sensor_id = 2
filter_type = 'HIGH'

pattern = f'*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2'
rd2_files = list(data_path.glob(pattern))

dates = set()
for f in rd2_files:
    m = re.search(r'SMP_(\d{8})', f.name)
    if m: dates.add(m.group(1))
all_dates = sorted(list(dates))
selected = random.sample(all_dates, 4)
selected.sort()

analyzer = VibrationAnalyzer()
date_str = selected[0]
files = [f for f in rd2_files if date_str in f.name]
print(f'Testing: {date_str}, files: {len(files)}')

parser = RD2Parser(str(files[0]))
res = parser.parse()
values = res['values']
fs = res['metadata'].get('sampling_frequency', 25600)
print(f'Values: {len(values)}, FS: {fs}')

try:
    print('Calling calculate_spectrum...')
    freq, amp = analyzer.calculate_spectrum(values, fs)
    print(f'Got: freq={type(freq)}, amp={type(amp)}')
    print(f'len(freq)={len(freq)}, len(amp)={len(amp)}')
    print(f'Type len: {type(len(freq))}')
    print(f'Value len: {len(freq)}')
    
    print('Checking condition...')
    cond = len(freq) > 0 and len(amp) > 0
    print(f'Condition result: {cond}')
    
    if cond:
        print('SUCCESS!')
except Exception as e:
    print(f'ERROR: {e}')
    traceback.print_exc()
