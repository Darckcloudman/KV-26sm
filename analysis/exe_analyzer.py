# -*- coding: utf-8 -*-
"""
Анализатор app.exe - PyInstaller упакованного приложения
"""

import os
import struct
import sys
import io
from pathlib import Path

# Настройка кодировки для вывода
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_exe_header(filepath):
    """Анализ заголовка PE файла"""
    print("=" * 60)
    print("АНАЛИЗ app.exe")
    print("=" * 60)
    
    file_size = os.path.getsize(filepath)
    print(f"\n[INFO] Файл: {filepath}")
    print(f"[INFO] Размер: {file_size:,} байт ({file_size / (1024*1024):.2f} MB)")
    
    with open(filepath, 'rb') as f:
        # Проверка MZ заголовка
        mz = f.read(2)
        print(f"\n🔹 MZ заголовок: {'✅ Да' if mz == b'MZ' else '❌ Нет'}")
        
        # Печать первых 200 байт для анализа
        f.seek(0)
        first_bytes = f.read(200)
        
        # Поиск строк
        text = first_bytes.decode('latin-1')
        print(f"\n📋 Первые 200 байт (ASCII):")
        printable = ''.join(c if 32 <= ord(c) < 127 else '.' for c in text)
        print(f"  {printable}")
        
def search_strings(filepath, min_length=4):
    """Поиск строк в exe файле"""
    print("\n" + "=" * 60)
    print("ПОИСК СТРОК В EXE")
    print("=" * 60)
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Поиск Python-специфичных строк
    python_keywords = [
        b'python', b'.pyc', b'.pyo', b'import', b'__main__',
        b'PyInstaller', b'PYZ', b'PKG', b'COLLECT',
        b'numpy', b'scipy', b'pandas', b'requests',
        b'vibration', b'sensor', b'rms', b'fft',
        b'rd2', b'rw2', b'turbine', b'smp12c'
    ]
    
    found = {}
    for keyword in python_keywords:
        count = data.count(keyword)
        if count > 0:
            found[keyword.decode('latin-1')] = count
    
    print("\n[DETECTED] Python-библиотеки и ключевые слова:")
    for keyword, count in sorted(found.items(), key=lambda x: -x[1]):
        print(f"  {keyword:20s}: {count} вхождений")
    
    # Поиск IP адресов
    import re
    ip_pattern = rb'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    ips = re.findall(ip_pattern, data)
    unique_ips = set(ips)
    
    if unique_ips:
        print(f"\n[NETWORK] Обнаруженные IP адреса:")
        for ip in sorted(unique_ips)[:10]:
            print(f"  {ip.decode('latin-1')}")
    
    # Поиск путей к файлам
    path_pattern = rb'[A-Za-z]:\\[\\a-zA-Z0-9_\\\\.]+'
    paths = re.findall(path_pattern, data)
    unique_paths = set(paths)
    
    if unique_paths:
        print(f"\n[PATHS] Обнаруженные пути:")
        for path in sorted(unique_paths)[:15]:
            try:
                print(f"  {path.decode('utf-8', errors='ignore')}")
            except:
                pass
    
def extract_pyz(filepath):
    """Попытка извлечь PYZ архив из PyInstaller exe"""
    print("\n" + "=" * 60)
    print("ПОИСК PYZ АРХИВА")
    print("=" * 60)
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Поиск маркера PYZ
    pyz_marker = data.find(b'PYZ:')
    if pyz_marker == -1:
        pyz_marker = data.find(b'PYZ-')
    
    if pyz_marker != -1:
        print(f"[OK] Обнаружен маркер PYZ на позиции {pyz_marker}")
        print("[INFO] PYZ архив может быть извлечен через pyinstxtractor")
    else:
        print("[WARN] Маркер PYZ не найден")
    
def analyze_pyinstaller_structure(filepath):
    """Анализ структуры PyInstaller приложения"""
    print("\n" + "=" * 60)
    print("СТРУКТУРА PYINSTALLER")
    print("=" * 60)
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Поиск таблицы таблиц PyInstaller
    # Структура: IMGTable, PYZ, PKG, COLLECT
    sections = []
    
    if b'IMGTable' in data:
        sections.append('IMGTable')
    if b'PYZ' in data:
        sections.append('PYZ (Python архив)')
    if b'PKG' in data:
        sections.append('PKG (упакованные данные)')
    if b'COLLECT' in data:
        sections.append('COLLECT (собранные файлы)')
    if b'PREFIX' in data:
        sections.append('PREFIX')
    if b'ENCRYPTION' in data:
        sections.append('ENCRYPTION (зашифровано)')
    
    print("\n[SECTIONS] Обнаруженные секции:")
    for section in sections:
        print(f"  - {section}")
    
    if not sections:
        print("  [WARN] Не удалось определить структуру")

def main():
    """Основная функция"""
    exe_path = r"D:\Сoding\pyton_src\App Analizer\app.exe"
    
    if not os.path.exists(exe_path):
        print(f"[ERROR] Файл не найден: {exe_path}")
        return
    
    # Анализ заголовка
    analyze_exe_header(exe_path)
    
    # Поиск строк
    search_strings(exe_path)
    
    # Извлечение PYZ
    extract_pyz(exe_path)
    
    # Структура PyInstaller
    analyze_pyinstaller_structure(exe_path)
    
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 60)
    print("""
Для полной декомпиляции используйте:

1. pyinstxtractor (извлечение файлов):
   pip install pyinstxtractor
   pyinstxtractor app.exe

2. pefile (анализ PE структуры):
   pip install pefile
   python -c "import pefile; pe = pefile.PE('app.exe'); print(pe.dump_info())"

3. strings (поиск строк):
   strings app.exe > strings.txt

4. ILSpy / dotPeek (если .NET):
   https://github.com/icsharpcode/ILSpy

5. Uncompyle6 (декомпиляция Python):
   pip install uncompype6
   uncompyle6 extracted_script.pyc
""")

if __name__ == '__main__':
    main()
