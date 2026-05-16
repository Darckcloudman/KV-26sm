"""Утилиты для работы с файлами"""

import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import List


class FileHandler:
    """Класс для работы с файлами"""
    
    @staticmethod
    def unzip(zip_path: str, dest_dir: str) -> Path:
        """Распаковка ZIP архива"""
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)
        
        return dest_path
    
    @staticmethod
    def find_rd2_files(directory: str) -> List[str]:
        """Рекурсивный поиск всех .rd2 файлов"""
        rd2_files = []
        dir_path = Path(directory)
        
        for ext in ['*.rd2', '*.rw2']:
            rd2_files.extend(str(p) for p in dir_path.rglob(ext))
        
        return sorted(rd2_files)
    
    @staticmethod
    def get_temp_directory(prefix: str = "smp12c_") -> Path:
        """Создание временной директории"""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        return temp_dir
    
    @staticmethod
    def cleanup_temp_directory(temp_dir: str) -> None:
        """Удаление временной директории"""
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print("Ошибка удаления временной директории: %s" % e)
