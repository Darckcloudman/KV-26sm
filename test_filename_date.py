# -*- coding: utf-8 -*-
"""
Проверка извлечения даты из имени файла
"""

from pathlib import Path
from datetime import datetime
import re

def parse_datetime_from_filename(file_path: Path):
    """Извлечь дату из имени файла."""
    filename = file_path.name
    print(f"Имя файла: {filename}")
    
    match = re.search(r'SMP_(\d{8})_\d+', filename)
    
    if match:
        date_str = match.group(1)
        print(f"Найдена дата в имени: {date_str}")
        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
            print(f"Распарсена дата: {dt}")
            return dt
        except ValueError as e:
            print(f"Ошибка парсинга: {e}")
    
    print("Дата не найдена")
    return None

# Тест на файлах из test_data
print("=" * 60)
print("ТЕСТ: Извлечение даты из имени файла")
print("=" * 60)

test_files = [
    Path("test_data/W1436 WTG37 SMP_20250901_38408_SENSOR_01_FILTER_W.rd2"),
    Path("test_data/W1436 WTG37 SMP_20250901_38408_SENSOR_01_LOW_W.rd2"),
    Path("test_data/W1436 WTG37 SMP_20250901_38408_SENSOR_01_HIGH_W.rd2"),
]

for file_path in test_files:
    print(f"\nПроверка: {file_path.name}")
    print(f"Существует: {file_path.exists()}")
    dt = parse_datetime_from_filename(file_path)
    print(f"Результат: {dt}")
    print("-" * 60)
