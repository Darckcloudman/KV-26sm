# -*- coding: utf-8 -*-
"""
Настройки приложения SMP12C VibroDiag Analyzer.

Сохраняются в JSON-файл app_settings.json рядом с приложением.
"""

import json
from pathlib import Path


# Файл настроек рядом с пакетом приложения
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "app_settings.json"


def load_settings() -> dict:
    """Загрузить настройки из файла."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_settings(settings: dict) -> None:
    """Сохранить настройки в файл."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Ошибка сохранения настроек: {e}")


def get_last_archive_dir() -> Path | None:
    """
    Получить путь к последней выбранной папке с архивами.
    
    Returns:
        Path если папка существует, иначе None.
    """
    settings = load_settings()
    path_str = settings.get('last_archive_dir')
    if path_str:
        path = Path(path_str)
        if path.exists() and path.is_dir():
            return path
    return None


def set_last_archive_dir(path: Path) -> None:
    """
    Сохранить путь к папке с архивами.
    
    Args:
        path: Путь к каталогу с архивами.
    """
    settings = load_settings()
    settings['last_archive_dir'] = str(path)
    save_settings(settings)
