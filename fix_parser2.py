import re

with open(r'D:/Coding/pyton_pro/app/smp12c_vibrodiag/parsers/rd2_parser.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line2 parsing
content = content.replace(
    "self.metadata['sampling_time'] = extract_number(line2[1])",
    "self.metadata['sampling_time'] = extract_number(line2[0])")
content = content.replace(
    "self.metadata['sampling_frequency'] = extract_number(line2[4])",
    "self.metadata['sampling_frequency'] = extract_number(line2[1])")
content = content.replace(
    "self.metadata['samples'] = int(extract_number(line2[7]))",
    "self.metadata['samples'] = int(extract_number(line2[2]))")
content = content.replace(
    'self.metadata["record_length"] = f"{line2[10]} s"  # Длина записи',
    "self.metadata['record_length'] = extract_number(line2[4])")

# Fix line3 parsing
content = content.replace(
    "self.metadata['generator_speed'] = int(extract_number(line3[1]))  # Скорость генератора",
    "self.metadata['generator_speed'] = int(extract_number(line3[0]))")
content = content.replace(
    "self.metadata['active_power'] = int(extract_number(line3[4]))  # Активная мощность",
    "self.metadata['active_power'] = int(extract_number(line3[1]))")
content = content.replace(
    "self.metadata['wind_speed'] = extract_number(line3[7])",
    "self.metadata['wind_speed'] = extract_number(line3[2])")
content = content.replace(
    "self.metadata['cumulative_power'] = extract_number(line3[10])",
    "self.metadata['cumulative_power'] = extract_number(line3[4])")

# Fix line4 parsing
content = content.replace(
    "self.metadata['device'] = line4[1]",
    "self.metadata['device'] = line4[0].replace('Device: ', '')")
content = content.replace(
    "self.metadata['device_serial'] = line4[3]",
    "self.metadata['device_serial'] = line4[1].replace('SN: ', '')")
content = content.replace(
    "self.metadata['mac_address'] = line4[5]",
    "self.metadata['mac_address'] = line4[2].replace('MAC: ', '')")
content = content.replace(
    "self.metadata['ip_address'] = line4[7]",
    "self.metadata['ip_address'] = line4[3].replace('IP: ', '')")
content = content.replace(
    "self.metadata['firmware_version'] = line4[9]",
    "self.metadata['firmware_version'] = line4[4].replace('FW: ', '')")

# Fix line5 parsing
content = content.replace(
    "self.metadata['config_number'] = int(extract_number(line5[1]))",
    "self.metadata['config_number'] = int(extract_number(line5[0]))")
content = content.replace(
    "self.metadata['config_table_version'] = int(extract_number(line5[3]))",
    "self.metadata['config_table_version'] = int(extract_number(line5[1]))")
content = content.replace(
    "self.metadata['layout_version'] = int(extract_number(line5[5]))",
    "self.metadata['layout_version'] = int(extract_number(line5[2]))")
content = content.replace(
    "self.metadata['exception_applied'] = int(extract_number(line5[7]))",
    "self.metadata['exception_applied'] = int(extract_number(line5[3]))")
content = content.replace(
    "self.metadata['plc_ip'] = line5[9]",
    "self.metadata['plc_ip'] = line5[4].replace('PLC: ', '')")

with open(r'D:/Coding/pyton_pro/app/smp12c_vibrodiag/parsers/rd2_parser.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('rd2_parser.py header fixed')
