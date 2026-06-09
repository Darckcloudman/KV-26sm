# -*- coding: utf-8 -*-
"""
Генерация PDF-отчётов по вибродиагностике ВЭУ.

Использует reportlab для создания профессиональных отчётов
в чёрно-белом стиле.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np

from ..dal.logger import get_logger

logger = get_logger("PDFReportGenerator")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        Image, PageBreak, KeepTogether
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("reportlab не установлен. PDF-отчёты недоступны.")


# === Глобальная настройка кириллицы ===
# Используем стандартные шрифты Windows с поддержкой кириллицы
CYRILLIC_FONT_NAME = 'Arial'  # Arial есть в Windows по умолчанию
CYRILLIC_FONT_BOLD = 'Arial-Bold'

def _try_register_cyrillic_fonts():
    """
    Попытка зарегистрировать шрифты с поддержкой кириллицы.
    Используем Arial из Windows или DejaVu Sans как fallback.
    """
    global CYRILLIC_FONT_NAME, CYRILLIC_FONT_BOLD
    
    if not HAS_REPORTLAB:
        logger.error("reportlab не установлен!")
        return
    
    import os
    import sys
    
    logger.info("=== НАЧАЛО РЕГИСТРАЦИИ ШРИФТОВ ===")
    logger.info("Платформа: %s", sys.platform)
    
    # Пути к шрифтам в порядке приоритета
    font_candidates = []
    
    # Windows - Arial
    if sys.platform.startswith('win'):
        logger.info("Обнаружена Windows, используем Arial")
        font_candidates = [
            ('Arial', r'C:\Windows\Fonts\arial.ttf'),
            ('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'),
        ]
    # macOS
    elif sys.platform.startswith('darwin'):
        logger.info("Обнаружена macOS, используем Arial")
        font_candidates = [
            ('Arial', '/Library/Fonts/Arial.ttf'),
            ('Arial-Bold', '/Library/Fonts/Arial Bold.ttf'),
        ]
    # Linux
    else:
        logger.info("Обнаружена Linux, используем DejaVuSans")
        font_candidates = [
            ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            ('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ]

    # Пробуем зарегистрировать шрифты
    registered = False
    for font_name, font_path in font_candidates:
        logger.info("Проверка шрифта: %s = %s", font_name, font_path)
        if os.path.exists(font_path):
            logger.info("Файл шрифта найден: %s", font_path)
            try:
                # Регистрируем TrueType шрифт с поддержкой Unicode
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                logger.info("[OK] Зарегистрирован шрифт: %s = %s", font_name, font_path)
                registered = True
                
                if font_name.lower().startswith('arial'):
                    CYRILLIC_FONT_NAME = 'Arial'
                    CYRILLIC_FONT_BOLD = 'Arial-Bold'
                elif font_name.lower().startswith('dejavu'):
                    CYRILLIC_FONT_NAME = 'DejaVuSans'
                    CYRILLIC_FONT_BOLD = 'DejaVuSans-Bold'
                    
            except Exception as e:
                logger.error("[ERROR] Ошибка регистрации шрифта %s: %s", font_path, e, exc_info=True)
        else:
            logger.warning("Файл шрифта НЕ найден: %s", font_path)
    
    if not registered:
        logger.error("[ERROR] Не удалось зарегистрировать ни один шрифт с кириллицей! Используем Helvetica.")
        CYRILLIC_FONT_NAME = 'Helvetica'
        CYRILLIC_FONT_BOLD = 'Helvetica-Bold'
    else:
        logger.info("=== ЗАВЕРШЕНИЕ РЕГИСТРАЦИИ ШРИФТОВ ===")
        logger.info("Используемый шрифт: %s (bold: %s)", CYRILLIC_FONT_NAME, CYRILLIC_FONT_BOLD)


# Регистрируем шрифты при загрузке модуля
if HAS_REPORTLAB:
    _try_register_cyrillic_fonts()


class PDFReportGenerator:
    """Генератор PDF-отчётов по вибродиагностике."""

    def __init__(self, parser, sensor_id: int = 1):
        """
        Инициализация генератора.

        Args:
            parser: Парсер с данными.
            sensor_id: ID датчика для отчёта (по умолчанию 1).
        """
        self.parser = parser
        self.sensor_id = sensor_id
        self.data = parser.get_sensor_data(sensor_id) if parser else None
        self.metrics = parser.get_turbine_metrics() if parser else {}

        # Получаем дату записи из метрик парсера
        self.record_date = self.metrics.get('record_datetime')
        
        # Если дата не найдена в метаданных, пробуем из имени файла
        if not self.record_date and parser and hasattr(parser, 'archive_path'):
            filepath = str(parser.archive_path)
            # Пробуем найти дату в формате YYYYMMDD или DDMMYYYY
            import re
            date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filepath)
            if date_match:
                try:
                    year, month, day = date_match.groups()
                    from datetime import datetime
                    self.record_date = f"{day}.{month}.{year}"
                except Exception:
                    pass

        # Группы датчиков (1-5 редуктор, 6-8 генератор)
        self.sensor_groups = {
            'Редуктор': [1, 2, 3, 4, 5],
            'Генератор': [6, 7, 8]
        }

        # Названия позиций датчиков
        self.sensor_positions = {
            1: 'Вход редуктора, радиальное направление',
            2: 'Передающая часть редуктора',
            3: 'Сателлит нижняя часть редуктора',
            4: 'Выход трансмиссии, радиальное направление',
            5: 'Выход трансмиссии, осевое направление',
            6: 'Подшипник генератора со стороны ротора, осевое направление',
            7: 'Подшипник генератора со стороны ротора, радиальное направление'
        }

        # Цвета (чёрно-белая тема) — лениво, только при наличии reportlab
        if HAS_REPORTLAB:
            self.COLOR_BLACK = colors.HexColor('#000000')
            self.COLOR_WHITE = colors.HexColor('#FFFFFF')
            self.COLOR_GRAY = colors.HexColor('#888888')
            self.COLOR_LIGHT_GRAY = colors.HexColor('#CCCCCC')
            self.COLOR_DARK_GRAY = colors.HexColor('#333333')

    def generate(self, file_path: Path, chart_images: Optional[Dict[str, str]] = None) -> bool:
        """
        Сгенерировать PDF-отчёт.

        Args:
            file_path: Путь для сохранения PDF.
            chart_images: Словарь {название: путь_к_png} для вставки графиков.

        Returns:
            True если генерация успешна.
        """
        if not HAS_REPORTLAB:
            logger.error("reportlab не установлен. Установите: pip install reportlab")
            return False

        try:
            file_path = Path(file_path)
            logger.info("Генерация PDF-отчёта: %s", file_path)

            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )

            story = []
            styles = getSampleStyleSheet()

            # Используем зарегистрированные шрифты с кириллицей
            font_name = CYRILLIC_FONT_NAME
            font_bold = CYRILLIC_FONT_BOLD

            # Кастомные стили с кириллическим шрифтом
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=self.COLOR_BLACK,
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName=font_bold
            )
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=self.COLOR_BLACK,
                spaceAfter=8,
                spaceBefore=12,
                fontName=font_bold
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=self.COLOR_BLACK,
                spaceAfter=6,
                fontName=font_name
            )
            info_style = ParagraphStyle(
                'CustomInfo',
                parent=styles['Normal'],
                fontSize=9,
                textColor=self.COLOR_GRAY,
                alignment=TA_RIGHT,
                fontName=font_name
            )

            # === Заголовок ===
            turbine_id = self.metrics.get('turbine_id', 'Не указано')
            wtg_id = self.metrics.get('wtg_id', '')
            
            # Извлекаем номер ВЭУ из WTG ID (приоритет) или из turbine ID
            # Форматы: WTG40 -> ВЭУ 40, W1436 -> ВЭУ 1436
            turbine_name = "ВЭУ"
            turbine_number = ""
            
            # Сначала пробуем WTG ID (приоритет)
            if wtg_id and str(wtg_id).startswith('WTG'):
                # WTG40 -> ВЭУ 40
                turbine_number = str(wtg_id)[3:]
                turbine_name = f"ВЭУ {turbine_number}"
            elif str(turbine_id).startswith('WTG'):
                turbine_number = str(turbine_id)[3:]
                turbine_name = f"ВЭУ {turbine_number}"
            elif str(turbine_id).startswith('W') and len(str(turbine_id)) > 1:
                # W1436 -> ВЭУ 1436
                turbine_number = str(turbine_id)[1:]
                turbine_name = f"ВЭУ {turbine_number}"
            elif str(turbine_id).isdigit():
                turbine_number = str(turbine_id)
                turbine_name = f"ВЭУ {turbine_number}"
            
            if not turbine_number:
                turbine_name = "ВЭУ"
            
            story.append(Paragraph(f"Отчёт по вибродиагностике {turbine_name}", title_style))
            
            # Добавляем информацию о дате записи (выровнено по центру)
            if self.record_date:
                try:
                    # Пробуем распарсить дату в разных форматах
                    date_str = str(self.record_date)
                    if '/' in date_str and len(date_str) > 10:
                        # Формат: 01/09/2025 23:50:37
                        date_part = date_str.split()[0] if ' ' in date_str else date_str
                        date_str = date_part.replace('/', '.')
                    elif len(date_str) == 8 and date_str.isdigit():
                        # Формат: 20250901
                        date_str = f"{date_str[6:8]}.{date_str[4:6]}.{date_str[:4]}"
                    elif ' ' in date_str:
                        # Формат: 01/09/2025 23:50:37
                        date_str = date_str.split(' ')[0].replace('/', '.')
                except Exception:
                    pass
            else:
                date_str = "Дата записи не указана"
            
            # Дата по центру
            info_style_centered = ParagraphStyle(
                'CustomInfoCentered',
                parent=styles['Normal'],
                fontSize=9,
                textColor=self.COLOR_GRAY,
                alignment=TA_CENTER,
                fontName=font_name
            )
            story.append(Paragraph(f"Дата записи: {date_str}", info_style_centered))
            story.append(Spacer(1, 4*mm))

            # === Информация о турбине ===
            story.append(Paragraph("1. Параметры турбины", heading_style))
            story.append(self._create_turbine_table())
            story.append(Spacer(1, 6*mm))

            # === Состояние датчиков ===
            story.append(Paragraph("2. Состояние датчиков", heading_style))
            story.append(self._create_sensors_table())
            story.append(Spacer(1, 6*mm))

            # === Топ-10 пиков для выбранного датчика ===
            # Получаем название позиции датчика
            sensor_position = self.sensor_positions.get(self.sensor_id, 'Не указано')
            peaks_title = f"3. Топ-10 пиков вибрации: Датчик {self.sensor_id} - {sensor_position}"
            story.append(Paragraph(peaks_title, heading_style))
            story.append(self._create_peaks_table())
            story.append(Spacer(1, 10*mm))

            # === Графики ===
            story.append(Paragraph("4. Графики вибрации", heading_style))
            if chart_images:
                for name, img_path in chart_images.items():
                    if Path(img_path).exists():
                        story.append(Paragraph(f"<b>{name}</b>", normal_style))
                        img = Image(str(img_path), width=170*mm, height=85*mm)
                        story.append(img)
                        story.append(Spacer(1, 4*mm))
            else:
                story.append(Paragraph("Графики недоступны", normal_style))

            # === Заключение ===
            story.append(Paragraph("5. Заключение", heading_style))
            conclusion = self._generate_conclusion()
            story.append(Paragraph(conclusion, normal_style))
            story.append(Spacer(1, 10*mm))

            # === Подвал ===
            story.append(Paragraph(
                f"KWF Prometheus v1.4.2 | {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                info_style
            ))

            doc.build(story)
            logger.info("PDF-отчёт создан: %s", file_path)
            return True

        except Exception as e:
            logger.error("Ошибка генерации PDF: %s", e, exc_info=True)
            return False

    def _create_turbine_table(self) -> Table:
        """Создать таблицу параметров турбины."""
        turbine_id = self.metrics.get('turbine_id', 'Не указано')
        wtg_id = self.metrics.get('wtg_id', '')
        
        data = [
            ['Параметр', 'Значение', 'Единица'],
            ['ID турбины', str(turbine_id), str(wtg_id) if wtg_id else '-'],
            ['Мощность', f"{self.metrics.get('power_kw', 0):.1f}", 'кВт'],
            ['Частота вращения', f"{self.metrics.get('generator_speed_rpm', 0):.1f}", 'об/мин'],
            ['Скорость ветра', f"{self.metrics.get('wind_speed_ms', 0):.1f}", 'м/с'],
            ['Накопленная выработка', f"{self.metrics.get('cumulative_power_kwh', 0):.1f}", 'кВт·ч'],
        ]
        return self._styled_table(data, col_widths=[60*mm, 40*mm, 30*mm])

    def _create_sensors_table(self) -> Table:
        """Создать таблицу состояния датчиков с группировкой."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        # Создаём таблицу с группировкой
        data = [['Группа', 'Датчик', 'НЧ RMS', 'ВЧ RMS', 'ВЧ(ф) RMS', 'Зона']]

        for group_name, sensor_ids in self.sensor_groups.items():
            for sid in sensor_ids:
                sensor_data = self.parser.get_sensor_data(sid)
                if sensor_data is None:
                    data.append([group_name, f'Датчик {sid}', '—', '—', '—', 'Нет данных'])
                    continue

                rms_values = []
                zones = []

                for signal_key in ['acceleration', 'velocity', 'high_freq']:
                    signal = sensor_data.get(signal_key)
                    if signal is not None:
                        rms = np.sqrt(np.mean(np.array(signal) ** 2))
                        rms_values.append(f"{rms:.4f}")
                        if signal_key == 'velocity':
                            zones.append(analyzer.determine_zone_vel(rms))
                        else:
                            zones.append(analyzer.determine_zone_acc(rms))
                    else:
                        rms_values.append('—')
                        zones.append('—')

                # Определяем общую зону (максимальная)
                zone_priorities = {'D': 4, 'C': 3, 'B': 2, 'A': 1, '-': 0, '—': 0}
                max_zone = max(zones, key=lambda z: zone_priorities.get(z, 0)) if zones else '—'

                data.append([group_name, f'Датчик {sid}'] + rms_values + [max_zone])

            # Добавляем пустую строку между группами (опционально)
            # data.append(['', '', '', '', '', ''])

        return self._styled_table_sensors(data, col_widths=[20*mm, 20*mm, 25*mm, 25*mm, 25*mm, 20*mm])

    def _create_peaks_table(self) -> Table:
        """Создать таблицу топ-10 пиков вибрации для выбранного датчика."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        sensor_data = self.parser.get_sensor_data(self.sensor_id)
        if sensor_data is None:
            return self._styled_table(
                [['Пик', 'Частота', 'Амплитуда', 'Тип']],
                col_widths=[30*mm, 40*mm, 40*mm, 30*mm]
            )

        # Собираем все пики из всех сигналов
        all_peaks = []

        # НЧ (ускорение)
        if sensor_data.get('acceleration') is not None and sensor_data.get('acceleration_fs'):
            acc = np.array(sensor_data['acceleration'])
            fs = sensor_data['acceleration_fs']
            freqs, amps = analyzer.calculate_spectrum(acc, fs)
            
            # Находим пики в диапазоне 0-1000 Гц
            for i in range(1, len(freqs) - 1):
                if amps[i] > amps[i-1] and amps[i] > amps[i+1] and freqs[i] <= 1000:
                    all_peaks.append({
                        'freq': freqs[i],
                        'amp': amps[i],
                        'type': 'НЧ (ускорение)'
                    })

        # ВЧ (скорость)
        if sensor_data.get('velocity') is not None and sensor_data.get('velocity_fs'):
            vel = np.array(sensor_data['velocity'])
            fs = sensor_data['velocity_fs']
            freqs, amps = analyzer.calculate_spectrum(vel, fs)
            
            for i in range(1, len(freqs) - 1):
                if amps[i] > amps[i-1] and amps[i] > amps[i+1] and freqs[i] <= 1000:
                    all_peaks.append({
                        'freq': freqs[i],
                        'amp': amps[i],
                        'type': 'ВЧ (скорость)'
                    })

        # ВЧ(ф) (высокочастотное ускорение)
        if sensor_data.get('high_freq') is not None and sensor_data.get('high_freq_fs'):
            hf = np.array(sensor_data['high_freq'])
            fs = sensor_data['high_freq_fs']
            freqs, amps = analyzer.calculate_spectrum(hf, fs)
            
            for i in range(1, len(freqs) - 1):
                if amps[i] > amps[i-1] and amps[i] > amps[i+1] and freqs[i] <= 1000:
                    all_peaks.append({
                        'freq': freqs[i],
                        'amp': amps[i],
                        'type': 'ВЧ(ф)'
                    })

        # Сортируем по амплитуде (по убыванию)
        all_peaks.sort(key=lambda x: x['amp'], reverse=True)
        
        # Берем топ-10
        top_peaks = all_peaks[:10]

        # Создаем таблицу
        data = [['#', 'Частота, Гц', 'Амплитуда', 'Тип']]
        for idx, peak in enumerate(top_peaks, 1):
            data.append([
                str(idx),
                f"{peak['freq']:.2f}",
                f"{peak['amp']:.4f}",
                peak['type']
            ])

        return self._styled_table(data, col_widths=[15*mm, 40*mm, 40*mm, 40*mm])

    def _generate_conclusion(self) -> str:
        """Сгенерировать текст заключения на основе зон."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        # Собираем все датчики с их зонами
        sensor_zones = {}
        zone_priorities = {'D': 4, 'C': 3, 'B': 2, 'A': 1, '-': 0, '—': 0}
        zone_names = {'A': 'Норма', 'B': 'Внимание', 'C': 'Требует внимания', 'D': 'Критично'}

        for sid in range(1, 9):
            sensor_data = self.parser.get_sensor_data(sid)
            if sensor_data is None:
                continue

            max_zone = 'A'
            max_priority = 0

            for signal_key in ['acceleration', 'velocity', 'high_freq']:
                signal = sensor_data.get(signal_key)
                if signal is not None:
                    rms = np.sqrt(np.mean(np.array(signal) ** 2))
                    if signal_key == 'velocity':
                        zone = analyzer.determine_zone_vel(rms)
                    else:
                        zone = analyzer.determine_zone_acc(rms)

                    priority = zone_priorities.get(zone, 0)
                    if priority > max_priority:
                        max_priority = priority
                        max_zone = zone

            if max_priority > 0:
                sensor_zones[sid] = {'zone': max_zone, 'priority': max_priority}

        if not sensor_zones:
            return "Все датчики в норме. Значения вибрации соответствуют зоне A (нормальное состояние). Рекомендуется продолжать регулярный мониторинг."

        # Сортируем по приоритету (от худшего к лучшему)
        sorted_sensors = sorted(sensor_zones.items(), key=lambda x: x[1]['priority'], reverse=True)
        worst_priority = sorted_sensors[0][1]['priority']
        worst_zone = sorted_sensors[0][1]['zone']

        # Находим все датчики в худшей зоне
        worst_zone_sensors = [sid for sid, data in sorted_sensors if data['priority'] == worst_priority]

        # Формируем текст заключения
        if worst_zone == 'A':
            return "Состояние турбины в норме. Все датчики показывают значения в зоне A (нормальное состояние). Рекомендуется продолжать регулярный мониторинг."
        elif worst_zone == 'B':
            sensor_list = ', '.join([f'Датчик {sid}' for sid in worst_zone_sensors])
            return f"Требуется внимание. {sensor_list} показывают значения в зоне B ({zone_names[worst_zone]}). Рекомендуется увеличить частоту проверок и рассмотреть плановое техническое обслуживание."
        elif worst_zone == 'C':
            sensor_list = ', '.join([f'Датчик {sid}' for sid in worst_zone_sensors])
            other_sensors = [sid for sid, data in sorted_sensors if data['priority'] < worst_priority and data['priority'] >= 2]
            if other_sensors:
                other_list = ', '.join([f'Датчик {sid}' for sid in other_sensors])
                return f"Требуется вмешательство. {sensor_list} показывают наихудшие значения в зоне C ({zone_names[worst_zone]}). {other_list} также показывают значения в зоне C и требуют проверки. Необходимо провести детальную диагностику и запланировать ремонтные работы."
            else:
                return f"Требуется вмешательство. {sensor_list} показывают значения в зоне C ({zone_names[worst_zone]}). Необходимо провести детальную диагностику и запланировать ремонтные работы."
        else:  # Zone D
            sensor_list = ', '.join([f'Датчик {sid}' for sid in worst_zone_sensors])
            other_c_sensors = [sid for sid, data in sorted_sensors if data['priority'] == 3]
            other_b_sensors = [sid for sid, data in sorted_sensors if data['priority'] == 2]
            
            conclusion = f"КРИТИЧНО! {sensor_list} показывают значения в зоне D ({zone_names[worst_zone]}). Требуется немедленная остановка оборудования и проведение аварийного ремонта."
            
            if other_c_sensors:
                conclusion += f" Датчики {', '.join([f'Датчик {sid}' for sid in other_c_sensors])} также в зоне C и требуют внимания."
            if other_b_sensors:
                conclusion += f" Датчики {', '.join([f'Датчик {sid}' for sid in other_b_sensors])} в зоне B - рекомендуется мониторинг."
            
            return conclusion

    def _styled_table(self, data: List[List[str]], col_widths: List[float]) -> Table:
        """Создать стилизованную таблицу с поддержкой кириллицы."""
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Используем зарегистрированные шрифты с кириллицей
        font_name = CYRILLIC_FONT_NAME
        font_bold = CYRILLIC_FONT_BOLD

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_BLACK),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLOR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLOR_WHITE),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.COLOR_BLACK),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLOR_WHITE, colors.HexColor('#F5F5F5')]),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ]

        # Подсветка зон
        zone_colors = {
            'A': colors.HexColor('#E8F5E9'),
            'B': colors.HexColor('#FFF9C4'),
            'C': colors.HexColor('#FFE0B2'),
            'D': colors.HexColor('#FFCDD2'),
        }

        for row_idx, row in enumerate(data[1:], start=1):
            zone = row[-1] if row else '-'
            if zone in zone_colors:
                style_commands.append(
                    ('BACKGROUND', (-1, row_idx), (-1, row_idx), zone_colors[zone])
                )

        table.setStyle(TableStyle(style_commands))
        return table

    def _styled_table_sensors(self, data: List[List[str]], col_widths: List[float]) -> Table:
        """Создать стилизованную таблицу датчиков с группировкой."""
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Используем зарегистрированные шрифты с кириллицей
        font_name = CYRILLIC_FONT_NAME
        font_bold = CYRILLIC_FONT_BOLD

        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_BLACK),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLOR_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), self.COLOR_WHITE),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.COLOR_BLACK),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLOR_WHITE, colors.HexColor('#F5F5F5')]),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Датчик слева
            ('ALIGN', (2, 0), (4, -1), 'CENTER'),  # RMS значения по центру
        ]

        # Подсветка зон
        zone_colors = {
            'A': colors.HexColor('#E8F5E9'),
            'B': colors.HexColor('#FFF9C4'),
            'C': colors.HexColor('#FFE0B2'),
            'D': colors.HexColor('#FFCDD2'),
        }

        for row_idx, row in enumerate(data[1:], start=1):
            zone = row[-1] if row else '-'
            if zone in zone_colors:
                style_commands.append(
                    ('BACKGROUND', (-1, row_idx), (-1, row_idx), zone_colors[zone])
                )

        table.setStyle(TableStyle(style_commands))
        return table
