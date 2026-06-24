# -*- coding: utf-8 -*-
"""
Тест парсинга даты из имени файла
"""

from datetime import datetime
import re

def parse_record_datetime(datetime_str: str):
    """Парсить дату-время из метаданных."""
    if not datetime_str:
        return None
    
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d_%H%M%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str.strip(), fmt)
        except ValueError:
            continue
    
    return None

def parse_datetime_from_filename(filename: str):
    """Извлечь дату из имени файла."""
    # Ищем паттерн SMP_YYYYMMDD
    match = re.search(r'SMP_(\d{8})_\d+', filename)
    
    if match:
        date_str = match.group(1)
        print(f"  Найдена дата в имени: {date_str}")
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            print(f"  Распарсена дата: {dt}")
            return dt
        except ValueError as e:
            print(f"  Ошибка парсинга: {e}")
    
    return None

# Тест
test_names = [
    "W1436 WTG37 SMP_20250701_38408_SENSOR_02_FILTER_W.rd2",
    "W1436 WTG37 SMP_20250901_38408_SENSOR_02_LOW_W.rd2",
]

print("Тест парсинга даты из имени файла:")
print("=" * 60)

for name in test_names:
    print(f"\n{name}")
    dt = parse_datetime_from_filename(name)
    print(f"  Результат: {dt}")
