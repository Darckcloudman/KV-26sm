# -*- coding: utf-8 -*-
"""
Утилита для анализа уникальности "серийного номера датчика".

Сканирует все .rd2 файлы в указанном корневом каталоге,
извлекает значение sensor_serial (первое поле строки 1),
и анализирует:
  1. Уникален ли номер в пределах одного датчика одного прибора?
  2. Уникален ли номер глобально?
  3. Может ли он служить дополнением к уникальному ключу?

Использование:
    python -m kwf_prometheus.utils.check_sensor_serial_uniqueness D:\\WindFarmData
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
import json


def extract_sensor_serial(file_path: Path) -> Tuple[str, str, str, str]:
    """
    Извлечь sensor_serial и метаданные из .rd2 файла.
    
    Returns:
        (sensor_serial, wtg_id, sensor_name, filter_type) или (None, ...)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if len(lines) < 1:
            return None, None, None, None
        
        # Строка 1: "38408;01/09/2025 23:45:29;38408;WTG37;Sensor_01;..."
        line1 = lines[0].strip()
        parts = line1.split(';')
        
        if len(parts) < 6:
            return None, None, None, None
        
        sensor_serial = parts[0].strip()
        wtg_id = parts[3].strip() if len(parts) > 3 else None
        sensor_name = parts[4].strip() if len(parts) > 4 else None
        
        # Определяем тип фильтра из имени файла
        fname_upper = file_path.name.upper()
        if '_LOW_W' in fname_upper or '_FILTER_W' in fname_upper:
            filter_type = 'LOW' if '_LOW_W' in fname_upper else 'FILTER'
        elif '_HIGH_' in fname_upper:
            filter_type = 'HIGH'
        else:
            filter_type = 'UNKNOWN'
        
        return sensor_serial, wtg_id, sensor_name, filter_type
        
    except Exception as e:
        print(f"Ошибка чтения {file_path}: {e}")
        return None, None, None, None


def analyze_storage(root_path: Path, max_files: int = None) -> Dict:
    """
    Проанализировать хранилище на уникальность sensor_serial.
    
    Args:
        root_path: Корневой каталог с архивами.
        max_files: Максимальное количество файлов для анализа (None = все).
        
    Returns:
        Словарь с результатами анализа.
    """
    print(f"Сканирование хранилища: {root_path}")
    
    # Собираем все .rd2 файлы
    rd2_files = list(root_path.rglob("*.rd2"))
    print(f"Найдено {len(rd2_files)} .rd2 файлов")
    
    if max_files:
        rd2_files = rd2_files[:max_files]
        print(f"Ограничение: анализируем первые {max_files} файлов")
    
    # Структуры для анализа
    # sensor_serial -> список файлов
    serial_to_files: Dict[str, List[Path]] = defaultdict(list)
    
    # (wtg_id, sensor_name) -> множество sensor_serial
    sensor_to_serials: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    
    # (wtg_id, sensor_name, filter_type) -> множество sensor_serial
    sensor_filter_to_serials: Dict[Tuple[str, str, str], Set[str]] = defaultdict(set)
    
    # Статистика
    total_processed = 0
    total_errors = 0
    
    for i, file_path in enumerate(rd2_files):
        if (i + 1) % 1000 == 0:
            print(f"  Обработано {i + 1}/{len(rd2_files)}...")
        
        serial, wtg_id, sensor_name, filter_type = extract_sensor_serial(file_path)
        
        if serial is None:
            total_errors += 1
            continue
        
        total_processed += 1
        serial_to_files[serial].append(file_path)
        
        if wtg_id and sensor_name:
            sensor_to_serials[(wtg_id, sensor_name)].add(serial)
            sensor_filter_to_serials[(wtg_id, sensor_name, filter_type)].add(serial)
    
    print(f"\nОбработано файлов: {total_processed}, ошибок: {total_errors}")
    
    # === Анализ 1: Уникальность в пределах одного датчика ===
    same_sensor_duplicates = 0
    same_sensor_total = 0
    
    for (wtg_id, sensor_name), serials in sensor_to_serials.items():
        same_sensor_total += 1
        if len(serials) > 1:
            same_sensor_duplicates += 1
    
    # === Анализ 2: Глобальная уникальность ===
    global_unique = len(serial_to_files)
    global_total = sum(len(files) for files in serial_to_files.values())
    global_duplicates = sum(1 for files in serial_to_files.values() if len(files) > 1)
    
    # === Анализ 3: Уникальность в пределах (датчик + фильтр) ===
    sensor_filter_duplicates = 0
    sensor_filter_total = 0
    
    for (wtg_id, sensor_name, filter_type), serials in sensor_filter_to_serials.items():
        sensor_filter_total += 1
        if len(serials) > 1:
            sensor_filter_duplicates += 1
    
    # === Статистика по повторениям ===
    duplicate_counts = defaultdict(int)
    for serial, files in serial_to_files.items():
        if len(files) > 1:
            duplicate_counts[len(files)] += 1
    
    # === Топ повторяющихся ===
    top_duplicates = sorted(
        [(serial, len(files)) for serial, files in serial_to_files.items() if len(files) > 1],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    results = {
        'total_files': len(rd2_files),
        'total_processed': total_processed,
        'total_errors': total_errors,
        'unique_serials': global_unique,
        'global_duplicates': global_duplicates,
        'same_sensor_total': same_sensor_total,
        'same_sensor_duplicates': same_sensor_duplicates,
        'sensor_filter_total': sensor_filter_total,
        'sensor_filter_duplicates': sensor_filter_duplicates,
        'duplicate_distribution': dict(duplicate_counts),
        'top_duplicates': [
            {'serial': serial, 'count': count, 'files': [str(f) for f in serial_to_files[serial][:3]]}
            for serial, count in top_duplicates
        ]
    }
    
    return results


def print_report(results: Dict):
    """Вывести отчёт в консоль."""
    print("\n" + "=" * 60)
    print("ОТЧЁТ О УНИКАЛЬНОСТИ СЕРИЙНОГО НОМЕРА ДАТЧИКА")
    print("=" * 60)
    
    print(f"\nВсего файлов: {results['total_files']}")
    print(f"Успешно обработано: {results['total_processed']}")
    print(f"Ошибок чтения: {results['total_errors']}")
    
    print(f"\n--- Глобальная уникальность ---")
    print(f"Уникальных серийных номеров: {results['unique_serials']}")
    print(f"Номеров с повторениями: {results['global_duplicates']}")
    if results['unique_serials'] > 0:
        pct = (results['global_duplicates'] / results['unique_serials']) * 100
        print(f"Процент дубликатов: {pct:.2f}%")
    
    print(f"\n--- Уникальность в пределах датчика ---")
    print(f"Всего (ВЭУ + датчик): {results['same_sensor_total']}")
    print(f"С дублирующимися serial: {results['same_sensor_duplicates']}")
    
    print(f"\n--- Уникальность в пределах (датчик + фильтр) ---")
    print(f"Всего (ВЭУ + датчик + фильтр): {results['sensor_filter_total']}")
    print(f"С дублирующимися serial: {results['sensor_filter_duplicates']}")
    
    print(f"\n--- Распределение повторений ---")
    for count, num_serials in sorted(results['duplicate_distribution'].items()):
        print(f"  {num_serials} номеров повторяются {count} раз(а)")
    
    print(f"\n--- Топ-10 повторяющихся номеров ---")
    for item in results['top_duplicates']:
        print(f"  {item['serial']}: {item['count']} файлов")
        for f in item['files'][:2]:
            print(f"    - {f}")
    
    print("\n" + "=" * 60)
    print("ВЫВОДЫ:")
    print("=" * 60)
    
    if results['global_duplicates'] == 0:
        print("✓ Серийный номер датчика ГЛОБАЛЬНО УНИКАЛЕН.")
        print("  Рекомендация: включить в уникальный ключ archives.")
    elif results['same_sensor_duplicates'] == 0:
        print("✓ Серийный номер уникален в пределах одного датчика.")
        print("  Рекомендация: использовать как вспомогательный идентификатор.")
    elif results['sensor_filter_duplicates'] == 0:
        print("✓ Серийный номер уникален в пределах (датчик + фильтр).")
        print("  Рекомендация: использовать как вспомогательный идентификатор.")
    else:
        print("✗ Серийный номер НЕ уникален даже в пределах одного датчика.")
        print("  Рекомендация: игнорировать для дедупликации.")
    
    print("=" * 60 + "\n")


def main():
    """Точка входа."""
    if len(sys.argv) < 2:
        print("Использование: python check_sensor_serial_uniqueness.py <корневой_каталог> [--max-files N]")
        print("Пример: python check_sensor_serial_uniqueness.py D:\\WindFarmData")
        sys.exit(1)
    
    root_path = Path(sys.argv[1])
    if not root_path.exists():
        print(f"Ошибка: каталог не найден: {root_path}")
        sys.exit(1)
    
    max_files = None
    if '--max-files' in sys.argv:
        idx = sys.argv.index('--max-files')
        if idx + 1 < len(sys.argv):
            max_files = int(sys.argv[idx + 1])
    
    results = analyze_storage(root_path, max_files)
    print_report(results)
    
    # Сохраняем JSON-отчёт
    report_path = Path("sensor_serial_analysis.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"JSON-отчёт сохранён: {report_path.absolute()}")


if __name__ == '__main__':
    main()
