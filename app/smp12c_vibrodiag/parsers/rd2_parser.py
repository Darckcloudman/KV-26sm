"""
РџР°СЂСЃРµСЂ С„Р°Р№Р»РѕРІ .rd2/.rw2 SMP12C

Р­С‚РѕС‚ РјРѕРґСѓР»СЊ РїСЂРµРґРѕСЃС‚Р°РІР»СЏРµС‚ РєР»Р°СЃСЃ РґР»СЏ С‡С‚РµРЅРёСЏ Рё Р°РЅР°Р»РёР·Р° С„Р°Р№Р»РѕРІ РІРёР±СЂРѕРґРёР°РіРЅРѕСЃС‚РёРєРё
РѕС‚ СЃРёСЃС‚РµРјС‹ SMP12C (Siemens Gamesa Renewable Energy).

Р¤РѕСЂРјР°С‚ С„Р°Р№Р»Р°: С‚РµРєСЃС‚РѕРІС‹Р№ CSV-РїРѕРґРѕР±РЅС‹Р№
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import os
import re

def extract_number(value: str) -> float:
    """Extract number from string with units (e.g. "25600 Hz" -> 25600.0)"""
    match = re.match(r'([\d.]+)', str(value).strip())
    return float(match.group(1)) if match else 0.0



class RD2Parser:
    """РџР°СЂСЃРµСЂ С„Р°Р№Р»РѕРІ .rd2/.rw2 SMP12C"""
    
    def __init__(self, filepath: str):
        """
        РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РїР°СЂСЃРµСЂР°
        
        Args:
            filepath: РїСѓС‚СЊ Рє С„Р°Р№Р»Сѓ .rd2 РёР»Рё .rw2
        """
        self.filepath = filepath
        self.metadata: Dict = {}
        self.data: Optional[np.ndarray] = None
        self.timestamps: Optional[np.ndarray] = None
        
    def parse(self) -> Dict:
        """
        РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ РїР°СЂСЃРёРЅРіР°
        Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃР»РѕРІР°СЂСЊ СЃ РјРµС‚Р°РґР°РЅРЅС‹РјРё Рё РґР°РЅРЅС‹РјРё
        
        Returns:
            СЃР»РѕРІР°СЂСЊ СЃ РєР»СЋС‡Р°РјРё:
            - metadata: dict СЃ РјРµС‚Р°РґР°РЅРЅС‹РјРё
            - timestamps: numpy array РІСЂРµРјРµРЅРЅС‹С… РјРµС‚РѕРє
            - values: numpy array Р·РЅР°С‡РµРЅРёР№ РІРёР±СЂРѕСЃРєРѕСЂРѕСЃС‚Рё
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Р¤Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ: {self.filepath}")
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # РџР°СЂСЃРёРЅРі Р·Р°РіРѕР»РѕРІРєР° (РїРµСЂРІС‹Рµ 5 СЃС‚СЂРѕРє)
        self._parse_header(lines[:5])
        
        # РџР°СЂСЃРёРЅРі РґР°РЅРЅС‹С… (РѕСЃС‚Р°Р»СЊРЅС‹Рµ СЃС‚СЂРѕРєРё)
        self._parse_data(lines[5:])
        
        return {
            'metadata': self.metadata,
            'timestamps': self.timestamps,
            'values': self.data
        }
    
    def _parse_header(self, header_lines: list):
        """РџР°СЂСЃРёРЅРі Р·Р°РіРѕР»РѕРІРєР° С„Р°Р№Р»Р°"""
        
        # РЎС‚СЂРѕРєР° 1: РћСЃРЅРѕРІРЅР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ
        line1 = header_lines[0].strip().split(', ')
        self.metadata['record_number'] = line1[0]  # РџРµСЂРІС‹Рµ 5 С†РёС„СЂ РЅРѕРјРµСЂР° Р·Р°РїРёСЃРё
        self.metadata['record_datetime'] = line1[1]  # Р”Р°С‚Р° Рё РІСЂРµРјСЏ
        self.metadata['turbine_id'] = line1[2]
        self.metadata['wtg_id'] = line1[3]
        self.metadata['sensor_name'] = line1[4]
        
        # РЎС‚СЂРѕРєР° 2: РџР°СЂР°РјРµС‚СЂС‹ РґРёСЃРєСЂРµС‚РёР·Р°С†РёРё
        line2 = header_lines[1].strip().split(', ')
        self.metadata['sampling_time'] = extract_number(line2[0])
        self.metadata['sampling_frequency'] = extract_number(line2[1])
        self.metadata['samples'] = int(extract_number(line2[2]))
        self.metadata['record_length'] = extract_number(line2[4])
        
        # РЎС‚СЂРѕРєР° 3: РџР°СЂР°РјРµС‚СЂС‹ С‚СѓСЂР±РёРЅС‹
        line3 = header_lines[2].strip().split(', ')
        self.metadata['generator_speed'] = int(extract_number(line3[0]))
        self.metadata['active_power'] = int(extract_number(line3[1]))
        self.metadata['wind_speed'] = extract_number(line3[2])
        self.metadata['cumulative_power'] = extract_number(line3[4])
        
        # РЎС‚СЂРѕРєР° 4: РРЅС„РѕСЂРјР°С†РёСЏ РѕР± СѓСЃС‚СЂРѕР№СЃС‚РІРµ
        line4 = header_lines[3].strip().split(', ')
        self.metadata['device'] = line4[0].replace('Device: ', '')
        self.metadata['device_serial'] = line4[1].replace('SN: ', '')
        self.metadata['mac_address'] = line4[2].replace('MAC: ', '')
        self.metadata['ip_address'] = line4[3].replace('IP: ', '')
        self.metadata['firmware_version'] = line4[4].replace('FW: ', '')
        
        # РЎС‚СЂРѕРєР° 5: РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ
        line5 = header_lines[4].strip().split(', ')
        self.metadata['config_number'] = int(extract_number(line5[0]))
        self.metadata['config_table_version'] = int(extract_number(line5[1]))
        self.metadata['layout_version'] = int(extract_number(line5[2]))
        self.metadata['exception_applied'] = int(extract_number(line5[3]))
        self.metadata['plc_ip'] = line5[4].replace('PLC: ', '')
    
    def _parse_data(self, data_lines: list):
        """РџР°СЂСЃРёРЅРі РґР°РЅРЅС‹С… РІРёР±СЂР°С†РёРё"""
        
        timestamps = []
        values = []
        
        for line in data_lines:
            if not line.strip():
                continue
            
            # РЈРґР°Р»СЏРµРј trailing Р·Р°РїСЏС‚СѓСЋ Рё СЂР°Р·РґРµР»СЏРµРј
            parts = line.strip().rstrip(',').split(', ')
            if len(parts) >= 3:
                try:
                    # parts[0] = РёРЅРґРµРєСЃ, parts[1] = РІСЂРµРјСЏ, parts[2] = Р·РЅР°С‡РµРЅРёРµ
                    timestamps.append(float(parts[1]))
                    values.append(float(parts[2]))
                except (ValueError, IndexError) as e:
                    # РџСЂРѕРїСѓСЃРєР°РµРј РЅРµРєРѕСЂСЂРµРєС‚РЅС‹Рµ СЃС‚СЂРѕРєРё
                    continue
        
        self.timestamps = np.array(timestamps)
        self.data = np.array(values)


class VibrationAnalyzer:
    """РђРЅР°Р»РёР·Р°С‚РѕСЂ РІРёР±СЂР°С†РёРѕРЅРЅС‹С… РґР°РЅРЅС‹С…"""
    
    @staticmethod
    def calculate_rms(values: np.ndarray, window_size: int = 1024) -> Dict:
        """
        Р’С‹С‡РёСЃР»РµРЅРёРµ СЃРєРѕР»СЊР·СЏС‰РµРіРѕ РЎРљР—
        
        Args:
            values: РјР°СЃСЃРёРІ Р·РЅР°С‡РµРЅРёР№ РІРёР±СЂРѕСЃРєРѕСЂРѕСЃС‚Рё
            window_size: СЂР°Р·РјРµСЂ РѕРєРЅР° РґР»СЏ СЂР°СЃС‡С‘С‚Р° РЎРљР—
        
        Returns:
            СЃР»РѕРІР°СЂСЊ СЃ СЂРµР·СѓР»СЊС‚Р°С‚Р°РјРё:
            - rms_values: СЃРїРёСЃРѕРє СЃР»РѕРІР°СЂРµР№ СЃ РІСЂРµРјРµРЅРЅС‹РјРё РјРµС‚РєР°РјРё Рё РЎРљР—
            - total_rms: РѕР±С‰РµРµ РЎРљР— РґР»СЏ РІСЃРµРіРѕ СЃРёРіРЅР°Р»Р°
            - peak: РїРёРєРѕРІРѕРµ Р·РЅР°С‡РµРЅРёРµ
            - peak_to_peak: СЂР°Р·РјР°С…
        """
        rms_values = []
        step = window_size // 2  # РџРµСЂРµРєСЂС‹С‚РёРµ 50%
        
        for i in range(0, len(values) - window_size, step):
            window = values[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            rms_values.append({
                'index': i,
                'rms': rms
            })
        
        # РћР±С‰РµРµ РЎРљР— РґР»СЏ РІСЃРµРіРѕ СЃРёРіРЅР°Р»Р°
        total_rms = np.sqrt(np.mean(values ** 2))
        
        return {
            'rms_values': rms_values,
            'total_rms': total_rms,
            'peak': np.max(np.abs(values)),
            'peak_to_peak': np.max(values) - np.min(values)
        }
    
    @staticmethod
    def calculate_spectrum(values: np.ndarray, sampling_freq: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Р’С‹С‡РёСЃР»РµРЅРёРµ СЃРїРµРєС‚СЂР° С‡РµСЂРµР· FFT
        
        Args:
            values: РјР°СЃСЃРёРІ Р·РЅР°С‡РµРЅРёР№ РІРёР±СЂРѕСЃРєРѕСЂРѕСЃС‚Рё
            sampling_freq: С‡Р°СЃС‚РѕС‚Р° РґРёСЃРєСЂРµС‚РёР·Р°С†РёРё (Р“С†)
        
        Returns:
            (frequencies, amplitudes) - С‡Р°СЃС‚РѕС‚С‹ Рё Р°РјРїР»РёС‚СѓРґС‹
        """
        n = len(values)
        
        # Р’С‹С‡РёСЃР»РµРЅРёРµ FFT
        fft_result = np.fft.rfft(values)
        
        # Р§Р°СЃС‚РѕС‚С‹
        frequencies = np.fft.rfftfreq(n, d=1/sampling_freq)
        
        # РђРјРїР»РёС‚СѓРґС‹ (Р°Р±СЃРѕР»СЋС‚РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ)
        amplitudes = np.abs(fft_result) * 2 / n
        
        # РЈР±РёСЂР°РµРј DC РєРѕРјРїРѕРЅРµРЅС‚Сѓ (0 Р“С†)
        frequencies = frequencies[1:]
        amplitudes = amplitudes[1:]
        
        return frequencies, amplitudes
    
    @staticmethod
    def determine_zone(rms_value: float) -> str:
        """
        РћРїСЂРµРґРµР»РµРЅРёРµ Р·РѕРЅС‹ СЃРѕСЃС‚РѕСЏРЅРёСЏ РїРѕ ISO 10816
        
        Р—РѕРЅС‹ РґР»СЏ РІРёР±СЂРѕСЃРєРѕСЂРѕСЃС‚Рё (РјРј/СЃ):
        - Zone A: < 2.3 РјРј/СЃ (РҐРѕСЂРѕС€Рѕ)
        - Zone B: 2.3 - 4.5 РјРј/СЃ (РЈРґРѕРІР»РµС‚РІРѕСЂРёС‚РµР»СЊРЅРѕ)
        - Zone C: 4.5 - 7.8 РјРј/СЃ (РќРµСѓРґРѕРІР»РµС‚РІРѕСЂРёС‚РµР»СЊРЅРѕ)
        - Zone D: > 7.8 РјРј/СЃ (РљСЂРёС‚РёС‡РЅРѕ)
        
        Args:
            rms_value: Р·РЅР°С‡РµРЅРёРµ РЎРљР— РІРёР±СЂРѕСЃРєРѕСЂРѕСЃС‚Рё
        
        Returns:
            'A', 'B', 'C' РёР»Рё 'D'
        """
        if rms_value < 2.3:
            return 'A'
        elif rms_value < 4.5:
            return 'B'
        elif rms_value < 7.8:
            return 'C'
        else:
            return 'D'
    
    @staticmethod
    def find_spectrum_peaks(frequencies: np.ndarray, amplitudes: np.ndarray, 
                           top_n: int = 10) -> List[Dict]:
        """
        РџРѕРёСЃРє РїРёРєРѕРІ РІ СЃРїРµРєС‚СЂРµ
        
        Args:
            frequencies: РјР°СЃСЃРёРІ С‡Р°СЃС‚РѕС‚
            amplitudes: РјР°СЃСЃРёРІ Р°РјРїР»РёС‚СѓРґ
            top_n: РєРѕР»РёС‡РµСЃС‚РІРѕ РїРёРєРѕРІ РґР»СЏ РІРѕР·РІСЂР°С‚Р°
        
        Returns:
            СЃРїРёСЃРѕРє РїРёРєРѕРІ СЃ С‡Р°СЃС‚РѕС‚РѕР№ Рё Р°РјРїР»РёС‚СѓРґРѕР№
        """
        # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ Р°РјРїР»РёС‚СѓРґРµ
        indices = np.argsort(amplitudes)[::-1][:top_n]
        
        peaks = []
        for idx in indices:
            peaks.append({
                'frequency': frequencies[idx],
                'amplitude': amplitudes[idx]
            })
        
        return peaks


def process_rd2_file(filepath: str) -> Dict:
    """
    РџРѕР»РЅС‹Р№ Р°Р»РіРѕСЂРёС‚Рј РѕР±СЂР°Р±РѕС‚РєРё С„Р°Р№Р»Р° .rd2
    
    Args:
        filepath: РїСѓС‚СЊ Рє С„Р°Р№Р»Сѓ
    
    Returns:
        СЃР»РѕРІР°СЂСЊ СЃРѕ РІСЃРµРјРё СЂРµР·СѓР»СЊС‚Р°С‚Р°РјРё:
        - metadata: РјРµС‚Р°РґР°РЅРЅС‹Рµ С„Р°Р№Р»Р°
        - rms: СЂРµР·СѓР»СЊС‚Р°С‚С‹ СЂР°СЃС‡С‘С‚Р° РЎРљР—
        - spectrum: СЃРїРµРєС‚СЂ (С‡Р°СЃС‚РѕС‚С‹ Рё Р°РјРїР»РёС‚СѓРґС‹)
        - zone: Р·РѕРЅР° СЃРѕСЃС‚РѕСЏРЅРёСЏ
        - peaks: РїРёРєРё РІ СЃРїРµРєС‚СЂРµ
        - raw_data: РёСЃС…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ
    """
    # 1. РџР°СЂСЃРёРЅРі С„Р°Р№Р»Р°
    parser = RD2Parser(filepath)
    result = parser.parse()
    
    metadata = result['metadata']
    values = result['values']
    timestamps = result['timestamps']
    
    if len(values) == 0:
        raise ValueError("Р¤Р°Р№Р» РЅРµ СЃРѕРґРµСЂР¶РёС‚ РґР°РЅРЅС‹С…")
    
    # 2. Р’С‹С‡РёСЃР»РµРЅРёРµ РЎРљР—
    analyzer = VibrationAnalyzer()
    rms_result = analyzer.calculate_rms(values)
    
    # 3. Р’С‹С‡РёСЃР»РµРЅРёРµ СЃРїРµРєС‚СЂР°
    frequencies, amplitudes = analyzer.calculate_spectrum(
        values, 
        metadata['sampling_frequency']
    )
    
    # 4. РћРїСЂРµРґРµР»РµРЅРёРµ Р·РѕРЅС‹
    zone = analyzer.determine_zone(rms_result['total_rms'])
    
    # 5. РџРѕРёСЃРє РїРёРєРѕРІ РІ СЃРїРµРєС‚СЂРµ
    peaks = analyzer.find_spectrum_peaks(frequencies, amplitudes)
    
    return {
        'metadata': metadata,
        'rms': rms_result,
        'spectrum': {
            'frequencies': frequencies,
            'amplitudes': amplitudes
        },
        'peaks': peaks,
        'zone': zone,
        'raw_data': {
            'timestamps': timestamps,
            'values': values
        }
    }


