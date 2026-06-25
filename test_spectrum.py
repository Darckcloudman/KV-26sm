from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, 'D:/Coding/pyton_pro')
from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer

f = Path(r'D:\Coding\pyton_pro\test_data\cascade_extracted\W1436 WTG37 SMP_20250902_38424_SENSOR_02_HIGH_W.rd2')
parser = RD2Parser(str(f))
res = parser.parse()
values = res['values']
fs = res['metadata'].get('sampling_frequency', 25600)
print(f'Values: {len(values)}, FS: {fs}')

analyzer = VibrationAnalyzer()
try:
    freq, amp = analyzer.calculate_spectrum(values, fs)
    print(f'Freq: {len(freq)}, Amp: {len(amp)}')
    print(f'Max amp: {max(amp) if len(amp) else 0}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
