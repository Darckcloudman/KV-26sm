# -*- coding: utf-8 -*-
"""
РўРµСЃС‚РѕРІС‹Р№ РјРѕРґСѓР»СЊ РґР»СЏ РїРѕСЃС‚СЂРѕРµРЅРёСЏ РєР°СЃРєР°РґРЅРѕРіРѕ РіСЂР°С„РёРєР° СЃРїРµРєС‚СЂРѕРІ (3D)
РСЃРїРѕР»СЊР·СѓРµС‚ РґР°РЅРЅС‹Рµ РёР· D:\Coding\pyton_pro\test_data\cascade_extracted

Р—Р°РїСѓСЃРє: python test_cascade_standalone.py

v1.5: РћРїС‚РёРјРёР·Р°С†РёСЏ - РѕР±РЅРѕРІР»РµРЅРёРµ РґР°РЅРЅС‹С… Р±РµР· РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ РіСЂР°С„РёРєР°
"""

import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import re
import time

# Р”РѕР±Р°РІР»СЏРµРј РїСѓС‚СЊ Рє РїСЂРѕРµРєС‚Сѓ РґР»СЏ РёРјРїРѕСЂС‚Р° РїР°СЂСЃРµСЂРѕРІ
sys.path.insert(0, str(Path(__file__).parent))

from kwf_prometheus.parsers.rd2_parser import RD2Parser, VibrationAnalyzer


class CascadeSpectrumViewer:
    """РџСЂРѕСЃРјРѕС‚СЂС‰РёРє РєР°СЃРєР°РґРЅС‹С… СЃРїРµРєС‚СЂРѕРІ СЃ GUI (РѕРїС‚РёРјРёР·РёСЂРѕРІР°РЅРЅС‹Р№)."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.spectra_data = {}
        self.all_dates = []
        self.analyzer = VibrationAnalyzer()
        self.current_sensor = 2
        self.show_7_spectra = False
        self.fig = None
        self.ax = None
        self.toggle_button = None
        self.buttons = []
        self.lines = []
        self.is_loading = False
    
    def load_spectra(self, sensor_id: int = 2, filter_type: str = "HIGH", show_7: bool = False):
        """Р—Р°РіСЂСѓР·РёС‚СЊ СЃРїРµРєС‚СЂС‹ РґР»СЏ РґР°С‚С‡РёРєР° Рё С‚РёРїР° С„РёР»СЊС‚СЂР°."""
        self.is_loading = True
        
        print(f"\n{'='*70}")
        print(f"Р—РђР“Р РЈР—РљРђ РЎРџР•РљРўР РћР’")
        print(f"{'='*70}")
        print(f"Р”Р°С‚С‡РёРє: {sensor_id}")
        print(f"Р¤РёР»СЊС‚СЂ: {filter_type}")
        print(f"РџРѕРєР°Р·Р°С‚СЊ: {'7' if show_7 else '4'} РіСЂР°С„РёРєР°")
        print()
        
        pattern = f"*SENSOR_{sensor_id:02d}_{filter_type}_*.rd2"
        rd2_files = list(self.data_path.glob(pattern))
        
        print(f"РџРѕРёСЃРє: {pattern}")
        print(f"РќР°Р№РґРµРЅРѕ С„Р°Р№Р»РѕРІ: {len(rd2_files)}")
        
        # РР·РІР»РµРєР°РµРј РґР°С‚С‹
        dates_found = set()
        for f in rd2_files:
            match = re.search(r'SMP_(\d{8})', f.name)
            if match:
                dates_found.add(match.group(1))
        
        self.all_dates = sorted(list(dates_found))
        print(f"Р”Р°С‚: {len(self.all_dates)}")
        
        if not self.all_dates:
            print("\n[ERROR] РќРµС‚ РґР°РЅРЅС‹С…!")
            self.is_loading = False
            return False
        
        # Р’С‹Р±РёСЂР°РµРј РґР°С‚С‹
        import random`n        n_select = 7 if show_7 else 4`n        selected_dates = random.sample(self.all_dates, min(n_select, len(self.all_dates)))`n        selected_dates.sort()
        print(f"Р’С‹Р±СЂР°РЅРѕ РґР°С‚: {len(selected_dates)}\n")
        
        # Р—Р°РіСЂСѓР¶Р°РµРј СЃРїРµРєС‚СЂС‹
        self.spectra_data = {}
        
        for date_str in selected_dates:
            matching_files = [f for f in rd2_files if date_str in f.name]
            
            if not matching_files:
                continue
            
            file_path = matching_files[0]
            
            try:
                parser = RD2Parser(str(file_path))
                result = parser.parse()
                
                if not result or 'values' not in result:
                    continue
                
                dt = datetime.strptime(date_str, "%Y%m%d")
                date_formatted = dt.strftime("%d.%m.%Y")
                
                values = result['values']
                sampling_freq = result['metadata'].get('sampling_frequency', 25600)
                
                if len(values) == 0:
                    continue
                
                frequencies, amplitudes = self.analyzer.calculate_spectrum(values, sampling_freq)
                
                if len(frequencies) and len(amplitudes):
                    self.spectra_data[date_formatted] = list(zip(frequencies, amplitudes))
                    
            except Exception as e:
                print(f"  [ERROR] {file_path.name}: {e}")
        
        print(f"\n{'='*70}")
        print(f"Р—РђР“Р РЈР–Р•РќРћ: {len(self.spectra_data)} СЃРїРµРєС‚СЂРѕРІ")
        print(f"{'='*70}\n")
        
        self.is_loading = False
        return len(self.spectra_data) > 0
    
    def plot_cascade(self, title: str = "РљР°СЃРєР°Рґ СЃРїРµРєС‚СЂРѕРІ"):
        """РџРѕСЃС‚СЂРѕРёС‚СЊ РЅР°С‡Р°Р»СЊРЅС‹Р№ РіСЂР°С„РёРє."""
        if not self.spectra_data:
            print("[ERROR] РќРµС‚ РґР°РЅРЅС‹С…")
            return
        
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle(title, fontsize=16, fontweight='bold')
        plt.subplots_adjust(top=0.88, right=0.75)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Р РёСЃСѓРµРј Р»РёРЅРёРё
        self._draw_lines()
        
        # РќР°СЃС‚СЂРѕР№РєР° РѕСЃРµР№
        self._setup_axes()
        
        # Р”РѕР±Р°РІР»СЏРµРј РєРЅРѕРїРєРё
        self._add_controls()
        
        # РЎРѕС…СЂР°РЅСЏРµРј
        output_path = Path(__file__).parent / "cascade_spectrum.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Р“СЂР°С„РёРє СЃРѕС…СЂР°РЅС‘РЅ: {output_path}")
        
        plt.show()
    
    def _draw_lines(self):
        """РќР°СЂРёСЃРѕРІР°С‚СЊ РІСЃРµ Р»РёРЅРёРё СЃРїРµРєС‚СЂРѕРІ."""
        iso_colors = {'A': '#2E7D32', 'B': '#F9A825', 'C': '#EF6C00', 'D': '#C62828'}
        
        # РћС‡РёС‰Р°РµРј СЃС‚Р°СЂС‹Рµ Р»РёРЅРёРё
        for line in self.lines:
            line.remove()
        self.lines = []
        
        sorted_dates = sorted(self.spectra_data.keys())
        
        for i, date_str in enumerate(sorted_dates):
            spectrum_points = self.spectra_data[date_str]
            frequencies = np.array([p[0] for p in spectrum_points])
            amplitudes = np.array([p[1] for p in spectrum_points])
            
            max_amp = np.max(amplitudes)
            zone = self._get_iso_zone(max_amp)
            color = iso_colors[zone]
            
            line, = self.ax.plot(frequencies, [i] * len(frequencies), amplitudes,
                               color=color, linewidth=1.2, label=f"{date_str} (Р—РѕРЅР° {zone})", alpha=0.9)
            self.lines.append(line)
    
    def _setup_axes(self):
        """РќР°СЃС‚СЂРѕРёС‚СЊ РѕСЃРё РіСЂР°С„РёРєР°."""
        sorted_dates = sorted(self.spectra_data.keys())
        n = len(sorted_dates)
        
        self.ax.set_xlabel('Р§Р°СЃС‚РѕС‚Р° (Р“С†)', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Р—Р°РїРёСЃРё (РїРѕ РґР°С‚Р°Рј)', fontsize=12, fontweight='bold')
        self.ax.set_zlabel('РђРјРїР»РёС‚СѓРґР°', fontsize=12, fontweight='bold')
        
        self.ax.set_yticks(range(n))
        self.ax.set_yticklabels(sorted_dates, fontsize=10)
        self.ax.view_init(elev=25, azim=-60)
        self.ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=9)
        self.ax.grid(True, alpha=0.3)
    
    def _add_controls(self):
        """Р”РѕР±Р°РІРёС‚СЊ РєРЅРѕРїРєРё СѓРїСЂР°РІР»РµРЅРёСЏ."""
        from matplotlib.widgets import Button
        
        btn_width = 0.04
        btn_height = 0.035
        start_y = 0.92
        
        # РљРЅРѕРїРєРё РґР°С‚С‡РёРєРѕРІ 1-8
        for sensor_id in range(1, 9):
            x_pos = 0.08 + (sensor_id - 1) * 0.05
            ax_btn = plt.axes([x_pos, start_y, btn_width, btn_height])
            
            color = '#4CAF50' if sensor_id == self.current_sensor else '#E0E0E0'
            text_color = 'white' if sensor_id == self.current_sensor else 'black'
            
            btn = Button(ax_btn, f'{sensor_id}', color=color, hovercolor='#8BC34A')
            btn.label.set_color(text_color)
            btn.label.set_weight('bold')
            btn.on_clicked(lambda event, sid=sensor_id: self._on_sensor_click(sid))
            self.buttons.append(btn)
        
        plt.figtext(0.02, 0.96, 'Р”Р°С‚С‡РёРє:', fontsize=11, fontweight='bold')
        
        # РўСѓРјР±Р»РµСЂ 4/7
        ax_toggle = plt.axes([0.55, start_y, 0.12, btn_height])
        toggle_label = '7 РіСЂР°С„РёРєРѕРІ' if self.show_7_spectra else '4 РіСЂР°С„РёРєР°'
        toggle_color = '#FF5722' if self.show_7_spectra else '#4CAF50'
        
        self.toggle_button = Button(ax_toggle, toggle_label, color=toggle_color, hovercolor='#FF8A65')
        self.toggle_button.label.set_color('white')
        self.toggle_button.label.set_weight('bold')
        self.toggle_button.on_clicked(self._on_toggle_click)
        
        plt.figtext(0.55, 0.96, 'РџРѕРєР°Р·Р°С‚СЊ:', fontsize=11, fontweight='bold')
    
    def _on_sensor_click(self, sensor_id: int):
        """РљР»РёРє РїРѕ РєРЅРѕРїРєРµ РґР°С‚С‡РёРєР° - РѕР±РЅРѕРІР»РµРЅРёРµ Р±РµР· РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ."""
        if self.is_loading:
            print("[WAIT] Р—Р°РіСЂСѓР·РєР°...")
            return
        
        print(f"\nР”Р°С‚С‡РёРє: {sensor_id}")
        self.current_sensor = sensor_id
        
        # РћР±РЅРѕРІР»СЏРµРј РєРЅРѕРїРєРё РІРёР·СѓР°Р»СЊРЅРѕ
        for i, btn in enumerate(self.buttons):
            sid = i + 1
            btn.color = '#4CAF50' if sid == sensor_id else '#E0E0E0'
            btn.label.set_color('white' if sid == sensor_id else 'black')
        
        # Р—Р°РіСЂСѓР¶Р°РµРј РґР°РЅРЅС‹Рµ
        loaded = self.load_spectra(sensor_id=sensor_id, filter_type="HIGH", show_7=self.show_7_spectra)
        
        if loaded:
            # РћР±РЅРѕРІР»СЏРµРј Р»РёРЅРёРё Рё РѕСЃРё
            self._draw_lines()
            self._setup_axes()
            
            # РћР±РЅРѕРІР»СЏРµРј Р·Р°РіРѕР»РѕРІРѕРє
            n = len(self.spectra_data)
            self.fig.suptitle(f"Р’Р­РЈ 37 - Р”Р°С‚С‡РёРє {sensor_id} (HIGH)\nРљР°СЃРєР°Рґ СЃРїРµРєС‚СЂРѕРІ Р·Р° {n} Р·Р°РїРёСЃРµР№",
                            fontsize=16, fontweight='bold')
            
            # РџРµСЂРµСЂРёСЃРѕРІРєР°
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
            
            # РЎРѕС…СЂР°РЅСЏРµРј
            output_path = Path(__file__).parent / "cascade_spectrum.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            
            print(f"  [OK] РћР±РЅРѕРІР»С‘РЅ")
        else:
            print(f"[ERROR] РќРµС‚ РґР°РЅРЅС‹С…")
            # Р’РѕР·РІСЂР°С‰Р°РµРј РєРЅРѕРїРєСѓ
            self.buttons[sensor_id-1].color = '#E0E0E0'
            self.buttons[sensor_id-1].label.set_color('black')
    
    def _on_toggle_click(self, event):
        """РљР»РёРє РїРѕ С‚СѓРјР±Р»РµСЂСѓ 4/7."""
        if self.is_loading:
            print("[WAIT] Р—Р°РіСЂСѓР·РєР°...")
            return
        
        self.show_7_spectra = not self.show_7_spectra
        n = 7 if self.show_7_spectra else 4
        
        print(f"\nРџРѕРєР°Р·Р°С‚СЊ: {n} РіСЂР°С„РёРєРѕРІ")
        
        # РћР±РЅРѕРІР»СЏРµРј С‚СѓРјР±Р»РµСЂ
        self.toggle_button.color = '#FF5722' if self.show_7_spectra else '#4CAF50'
        self.toggle_button.label.set_text('7 РіСЂР°С„РёРєРѕРІ' if self.show_7_spectra else '4 РіСЂР°С„РёРєР°')
        
        # Р—Р°РіСЂСѓР¶Р°РµРј РґР°РЅРЅС‹Рµ
        loaded = self.load_spectra(sensor_id=self.current_sensor, filter_type="HIGH", show_7=self.show_7_spectra)
        
        if loaded:
            self._draw_lines()
            self._setup_axes()
            
            n = len(self.spectra_data)
            self.fig.suptitle(f"Р’Р­РЈ 37 - Р”Р°С‚С‡РёРє {self.current_sensor} (HIGH)\nРљР°СЃРєР°Рґ СЃРїРµРєС‚СЂРѕРІ Р·Р° {n} Р·Р°РїРёСЃРµР№",
                            fontsize=16, fontweight='bold')
            
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
            
            output_path = Path(__file__).parent / "cascade_spectrum.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            
            print(f"  [OK] РћР±РЅРѕРІР»С‘РЅ")
        else:
            # Р’РѕР·РІСЂР°С‰Р°РµРј РѕР±СЂР°С‚РЅРѕ
            self.show_7_spectra = not self.show_7_spectra
            print("[ERROR] РќРµС‚ РґР°РЅРЅС‹С…")
    
    def _get_iso_zone(self, rms_value: float) -> str:
        """РћРїСЂРµРґРµР»РёС‚СЊ Р·РѕРЅСѓ РїРѕ ISO 10816."""
        normalized = rms_value * 10
        if normalized < 2.3: return 'A'
        elif normalized < 4.5: return 'B'
        elif normalized < 7.8: return 'C'
        else: return 'D'


def main():
    """РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ."""
    print("="*70)
    print("CASCADE SPECTRUM VIEWER v1.5")
    print("РћРїС‚РёРјРёР·РёСЂРѕРІР°РЅРЅС‹Р№ (Р±РµР· РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ РіСЂР°С„РёРєР°)")
    print("="*70)
    
    data_path = Path(r"D:\Coding\pyton_pro\test_data\cascade_extracted")
    
    if not data_path.exists():
        print(f"\n[ERROR] РџР°РїРєР° РЅРµ РЅР°Р№РґРµРЅР°: {data_path}")
        input("\nРќР°Р¶РјРёС‚Рµ Enter...")
        return
    
    viewer = CascadeSpectrumViewer(data_path)
    
    # Р—Р°РіСЂСѓР¶Р°РµРј РЅР°С‡Р°Р»СЊРЅС‹Рµ РґР°РЅРЅС‹Рµ
    loaded = viewer.load_spectra(sensor_id=2, filter_type="HIGH", show_7=False)
    
    if not loaded:
        print("\n[ERROR] РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ")
        input("\nРќР°Р¶РјРёС‚Рµ Enter...")
        return
    
    # РЎС‚СЂРѕРёРј РіСЂР°С„РёРє
    title = f"Р’Р­РЈ 37 - Р”Р°С‚С‡РёРє 2 (HIGH)\nРљР°СЃРєР°Рґ СЃРїРµРєС‚СЂРѕРІ Р·Р° {len(viewer.spectra_data)} Р·Р°РїРёСЃРµР№"
    viewer.plot_cascade(title=title)
    
    print("\n" + "="*70)
    print("Р“РћРўРћР’Рћ")
    print("="*70)
    print("\nРЈРїСЂР°РІР»РµРЅРёРµ:")
    print("  1-8: Р’С‹Р±РѕСЂ РґР°С‚С‡РёРєР°")
    print("  4/7: РџРµСЂРµРєР»СЋС‡Р°С‚РµР»СЊ РєРѕР»РёС‡РµСЃС‚РІР° РіСЂР°С„РёРєРѕРІ")
    print("\n[INFO] Р“СЂР°С„РёРєРё РѕР±РЅРѕРІР»СЏСЋС‚СЃСЏ Р±РµР· РїРµСЂРµСЃРѕР·РґР°РЅРёСЏ РѕРєРЅР°")
    input("\nРќР°Р¶РјРёС‚Рµ Enter...")


if __name__ == "__main__":
    main()


