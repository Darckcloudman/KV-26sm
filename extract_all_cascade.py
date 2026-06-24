# -*- coding: utf-8 -*-
"""
Распаковка всех ZIP архивов для каскада спектров
"""

import zipfile
from pathlib import Path

cascade_test = Path(r"D:\Coding\pyton_pro\test_data\cascade_test")
extract_base = Path(r"D:\Coding\pyton_pro\test_data\cascade_all")

extract_base.mkdir(exist_ok=True)

zip_files = list(cascade_test.glob("*.zip"))
print(f"Найдено ZIP файлов: {len(zip_files)}\n")

for zip_path in zip_files:
    # Извлекаем дату из имени файла
    date_str = zip_path.name.split("SMP_")[1].split("_")[0] if "SMP_" in zip_path.name else "unknown"
    extract_folder = extract_base / f"{date_str}"
    extract_folder.mkdir(exist_ok=True)
    
    print(f"Распаковка: {zip_path.name}")
    print(f"  → {extract_folder}")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

print(f"\n✅ Готово! Файлы распакованы в {extract_base}")
