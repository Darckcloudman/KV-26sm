"""Утилиты для работы с файлами"""

import zipfile
import shutil
from pathlib import Path
from typing import List
import matplotlib.figure


class FileHandler:
    """Класс для работы с файлами"""
    
    @staticmethod
    def unzip(zip_path: str, dest_dir: str) -> Path:
        """
        Распаковка ZIP архива
        
        Args:
            zip_path: путь к ZIP файлу
            dest_dir: директория для распаковки
        
        Returns:
            Path к директории с распакованными файлами
        """
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)
        
        return dest_path
    
    @staticmethod
    def find_rd2_files(directory: str) -> List[str]:
        """
        Рекурсивный поиск всех .rd2 файлов
        
        Args:
            directory: корневая директория для поиска
        
        Returns:
            список путей к .rd2 файлам
        """
        rd2_files = []
        dir_path = Path(directory)
        
        for ext in ['*.rd2', '*.rw2']:
            rd2_files.extend(str(p) for p in dir_path.rglob(ext))
        
        return sorted(rd2_files)
    
    @staticmethod
    def save_graph(fig: matplotlib.figure.Figure, filepath: str) -> bool:
        """
        Сохранение графика в PNG
        
        Args:
            fig: объект figure matplotlib
            filepath: путь для сохранения
        
        Returns:
            True если успешно, False иначе
        """
        try:
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            return True
        except Exception as e:
            print(f"Ошибка сохранения графика: {e}")
            return False
    
    @staticmethod
    def get_temp_directory(prefix: str = "smp12c_") -> Path:
        """
        Создание временной директории
        
        Args:
            prefix: префикс для имени директории
        
        Returns:
            Path к временной директории
        """
        import tempfile
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        return temp_dir
    
    @staticmethod
    def cleanup_temp_directory(temp_dir: str) -> None:
        """
        Удаление временной директории
        
        Args:
            temp_dir: путь к временной директории
        """
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Ошибка удаления временной директории: {e}")
