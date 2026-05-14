# -*- coding: utf-8 -*-
"""
Извлечение строк из app.pyc для анализа логики
"""

import os
import re

def extract_strings_from_pyc(pyc_path, min_length=5):
    """Извлечение читаемых строк из .pyc файла"""
    
    with open(pyc_path, 'rb') as f:
        data = f.read()
    
    print("=" * 60)
    print("ИЗВЛЕЧЕНИЕ СТРОК ИЗ app.pyc")
    print("=" * 60)
    print(f"\n[INFO] Файл: {pyc_path}")
    print(f"[INFO] Размер: {len(data):,} байт")
    
    # Поиск строк Python
    # Ищем паттерны вроде 'имя_переменной' или "строка"
    pattern = rb'[\x20-\x7e]{5,100}'
    matches = re.findall(pattern, data)
    
    # Фильтруем уникальные строки
    unique_strings = set()
    for m in matches:
        try:
            s = m.decode('ascii')
            if len(s) >= min_length:
                unique_strings.add(s)
        except:
            pass
    
    print(f"\n[INFO] Найдено строк: {len(unique_strings)}")
    
    # Ключевые паттерны для поиска
    keywords = [
        'rd2', 'rw2', 'smp', 'turbine', 'sensor', 'vibration',
        'rms', 'fft', 'zone', 'alert', 'warning', 'error',
        'http', 'api', 'request', 'response', 'json',
        'plot', 'chart', 'graph', 'matplotlib', 'pyqt',
        'file', 'open', 'read', 'write', 'save',
        'def ', 'class ', 'import ', 'from ',
        '192.168', 'localhost', '8000', '3000',
        'numpy', 'scipy', 'pandas'
    ]
    
    print("\n[KEYWORDS] Поиск по ключевым словам:")
    for kw in keywords:
        count = len([s for s in unique_strings if kw.lower() in s.lower()])
        if count > 0:
            print(f"  {kw:20s}: {count} совпадений")
    
    # Показать все строки с 'rd2' или 'smp'
    print("\n[STRINGS] Строки с 'rd2', 'rw2', 'smp':")
    for s in sorted(unique_strings):
        if any(kw in s.lower() for kw in ['rd2', 'rw2', 'smp', 'turbine', 'sensor']):
            print(f"  {s}")
    
    # Показать функции/классы
    print("\n[CODE] Обнаруженные функции/классы:")
    func_pattern = rb'(def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    funcs = re.findall(func_pattern, data)
    for func_type, func_name in funcs[:20]:
        print(f"  {func_type.decode()} {func_name.decode()}")
    
    # Показать импорты
    print("\n[IMPORTS] Обнаруженные импорты:")
    import_patterns = [
        rb'import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        rb'from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import'
    ]
    imports = set()
    for pattern in import_patterns:
        matches = re.findall(pattern, data)
        for m in matches:
            try:
                imports.add(m.decode('ascii'))
            except:
                pass
    
    for imp in sorted(imports)[:30]:
        print(f"  import {imp}")
    
    # Сохранить все строки в файл
    output_file = pyc_path.replace('.pyc', '_strings.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        for s in sorted(unique_strings):
            f.write(s + '\n')
    
    print(f"\n[OK] Все строки сохранены: {output_file}")

def main():
    pyc_file = r"D:\Сoding\pyton_src\App Analizer\app.exe_extracted\app.pyc"
    
    if not os.path.exists(pyc_file):
        print(f"[ERROR] Файл не найден: {pyc_file}")
        return
    
    extract_strings_from_pyc(pyc_file)

if __name__ == '__main__':
    main()
