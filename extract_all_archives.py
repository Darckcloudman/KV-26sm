# -*- coding: utf-8 -*-
"""
Распаковка всех ZIP архивов из cascade_test в cascade_extracted
"""

import zipfile
from pathlib import Path
import shutil

# Пути
source_path = Path(r"D:\Coding\pyton_pro\test_data\cascade_test")
extract_path = Path(r"D:\Coding\pyton_pro\test_data\cascade_extracted")

print("="*70)
print("РАСКОВКА ВСЕХ АРХИВОВ")
print("="*70)

# Очищаем папку назначения
if extract_path.exists():
    shutil.rmtree(extract_path)
    print(f"[OK] Папка очищена: {extract_path}")

extract_path.mkdir(parents=True, exist_ok=True)
print(f"[OK] Папка создана: {extract_path}\n")

# Находим все ZIP файлы
zip_files = list(source_path.glob("*.zip"))
print(f"Найдено ZIP архивов: {len(zip_files)}\n")

# Распаковываем каждый
for zip_file in zip_files:
    print(f"Распаковка: {zip_file.name}")
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            # Извлекаем все .rd2 файлы
            rd2_files = [f for f in zf.namelist() if f.endswith('.rd2')]
            
            for member in rd2_files:
                # Извлекаем с новым именем чтобы избежать коллизий
                zf.extract(member, extract_path)
            
            print(f"  [OK] Извлечено файлов: {len(rd2_files)}")
            
    except Exception as e:
        print(f"  [ERROR] {e}")

# Показываем результат
print("\n" + "="*70)
print("РЕЗУЛЬТАТ")
print("="*70)

rd2_files = list(extract_path.glob("*.rd2"))
print(f"Всего .rd2 файлов: {len(rd2_files)}")

# Группируем по датам
from collections import defaultdict
by_date = defaultdict(list)

for f in rd2_files:
    # Извлекаем дату из имени
    import re
    match = re.search(r'SMP_(\d{8})', f.name)
    if match:
        date = match.group(1)
        by_date[date].append(f.name)

print(f"\nФайлов по датам:")
for date in sorted(by_date.keys()):
    files = by_date[date]
    print(f"  {date}: {len(files)} файлов")

print("\n" + "="*70)
print("ГОТОВО!")
print("="*70)
print(f"\nПапка: {extract_path}")
print(f"Теперь можно запустить: python test_cascade_standalone.py")
