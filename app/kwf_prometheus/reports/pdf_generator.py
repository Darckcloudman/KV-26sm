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
            story.append(Paragraph("Отчёт по вибродиагностике ВЭУ", title_style))
            story.append(Spacer(1, 4*mm))

            # === Информация о турбине ===
            story.append(Paragraph("1. Параметры турбины", heading_style))
            story.append(self._create_turbine_table())
            story.append(Spacer(1, 6*mm))

            # === Состояние датчиков ===
            story.append(Paragraph("2. Состояние датчиков", heading_style))
            story.append(self._create_sensors_table())
            story.append(Spacer(1, 6*mm))

            # === Графики ===
            if chart_images:
                story.append(Paragraph("3. Графики вибрации", heading_style))
                for name, img_path in chart_images.items():
                    if Path(img_path).exists():
                        story.append(Paragraph(f"<b>{name}</b>", normal_style))
                        img = Image(str(img_path), width=170*mm, height=85*mm)
                        story.append(img)
                        story.append(Spacer(1, 4*mm))

            # === Заключение ===
            story.append(Paragraph("4. Заключение", heading_style))
            conclusion = self._generate_conclusion()
            story.append(Paragraph(conclusion, normal_style))
            story.append(Spacer(1, 10*mm))

            # === Подвал ===
            story.append(Paragraph(
                f"KWF Prometheus v1.4.1 | Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')} | A.Telezhenko, 2026",
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
        data = [
            ['Параметр', 'Значение', 'Единица'],
            ['Мощность', f"{self.metrics.get('power_kw', 0):.1f}", 'кВт'],
            ['Частота вращения', f"{self.metrics.get('generator_speed_rpm', 0):.1f}", 'об/мин'],
            ['Скорость ветра', f"{self.metrics.get('wind_speed_ms', 0):.1f}", 'м/с'],
            ['Накопленная выработка', f"{self.metrics.get('cumulative_power_kwh', 0):.1f}", 'кВт·ч'],
        ]
        return self._styled_table(data, col_widths=[60*mm, 40*mm, 30*mm])

    def _create_sensors_table(self) -> Table:
        """Создать таблицу состояния датчиков."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        data = [['Датчик', 'НЧ RMS', 'ВЧ RMS', 'ВЧ(ф) RMS', 'Зона']]

        for sid in range(1, 9):
            sensor_data = self.parser.get_sensor_data(sid)
            if sensor_data is None:
                data.append([f'Датчик {sid}', '—', '—', '—', 'Нет данных'])
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

            data.append([f'Датчик {sid}'] + rms_values + [max_zone])

        return self._styled_table(data, col_widths=[30*mm, 30*mm, 30*mm, 30*mm, 25*mm])

    def _generate_conclusion(self) -> str:
        """Сгенерировать текст заключения на основе зон."""
        from ..utils.vibration_analysis import VibrationAnalyzer
        analyzer = VibrationAnalyzer()

        max_priority = 0
        worst_sensor = None
        worst_zone = 'A'
        zone_names = {'A': 'Норма', 'B': 'Внимание', 'C': 'Требует внимания', 'D': 'Критично'}
        zone_priorities = {'D': 4, 'C': 3, 'B': 2, 'A': 1, '-': 0}

        for sid in range(1, 9):
            sensor_data = self.parser.get_sensor_data(sid)
            if sensor_data is None:
                continue

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
                        worst_sensor = sid
                        worst_zone = zone

        if max_priority == 0:
            return "Все датчики в норме. Значения вибрации соответствуют зоне A (нормальное состояние). Рекомендуется продолжать регулярный мониторинг."
        elif worst_zone == 'A':
            return f"Состояние турбины в норме. Максимальная зона — A (нормальное состояние). Рекомендуется продолжать регулярный мониторинг."
        elif worst_zone == 'B':
            return f"Требуется внимание. Датчик {worst_sensor} показывает значения в зоне B. Рекомендуется увеличить частоту проверок и рассмотреть плановое техническое обслуживание."
        elif worst_zone == 'C':
            return f"Требуется вмешательство. Датчик {worst_sensor} показывает значения в зоне C. Необходимо провести детальную диагностику и запланировать ремонтные работы."
        else:
            return f"КРИТИЧНО! Датчик {worst_sensor} показывает значения в зоне D. Требуется немедленная остановка оборудования и проведение аварийного ремонта."

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
