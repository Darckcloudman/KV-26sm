# -*- coding: utf-8 -*-
"""
Декомпиляция app.pyc из app.exe
"""

import os
import sys
from pathlib import Path

def decompile_pyc(pyc_path, output_dir):
    """Декомпиляция одного .pyc файла"""
    try:
        import uncompyle6
        from uncompyle6.main import decompile
        
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, os.path.basename(pyc_path).replace('.pyc', '.py'))
        
        print(f"[INFO] Декомпиляция: {pyc_path}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            sys.stdout = f
            decompile(312, pyc_path, output_stream=f)
            sys.stdout = sys.__stdout__
        
        print(f"[OK] Сохранено: {output_file}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка декомпиляции {pyc_path}: {e}")
        return False

def main():
    # Путь к извлечённому app.pyc
    pyc_file = r"D:\Сoding\pyton_src\App Analizer\app.exe_extracted\app.pyc"
    output_dir = r"D:\Сoding\pyton_pro\analysis\decompiled"
    
    if not os.path.exists(pyc_file):
        print(f"[ERROR] Файл не найден: {pyc_file}")
        return
    
    print("=" * 60)
    print("ДЕКОМПИЛЯЦИЯ app.pyc")
    print("=" * 60)
    
    success = decompile_pyc(pyc_file, output_dir)
    
    if success:
        print("\n[SUCCESS] Декомпиляция завершена!")
        print(f"Результат: {output_dir}")
        
        # Показать первые строки
        py_file = os.path.join(output_dir, "app.py")
        if os.path.exists(py_file):
            print("\n[PREVIEW] Первые 50 строк декомпилированного кода:")
            print("-" * 60)
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:50]
                for line in lines:
                    print(line.rstrip())
            print("-" * 60)
    else:
        print("\n[FAILED] Декомпиляция не удалась")

if __name__ == '__main__':
    main()
