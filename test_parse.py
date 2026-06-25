from pathlib import Path
from kwf_prometheus.parsers.rd2_parser import RD2Parser

f = Path(r'D:\Coding\pyton_pro\test_data\cascade_extracted\W1436 WTG37 SMP_20250902_38424_SENSOR_02_HIGH_W.rd2')
print(f'File exists: {f.exists()}')
try:
    parser = RD2Parser(str(f))
    res = parser.parse()
    print(f'Parse result: {type(res)}')
    print(f'Keys: {res.keys() if res else None}')
    if res and 'values' in res:
        v = res['values']
        print(f'Values: {len(v)} points')
    else:
        print('No values in result!')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
