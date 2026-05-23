"""Тесты для KWF Prometheus v2.0.0"""
import unittest
import numpy as np
import tempfile
from smp12c_vibrodiag.parsers.rd2_parser import RD2Parser, VibrationAnalyzer, process_rd2_file

class TestRD2Parser(unittest.TestCase):
    def test_parse_header(self):
        test_data = """00001, 2024-01-15 10:30:45, WTG06, SMP12C-001, SENSOR_01_LOW_W
0.001 s, 25600 Hz, 131072 samples, 00001, 5.120 s
1500 RPM, 2500 KW, 12.5 m/s, 00001234, 50000.0 kWh
Device: SMP12C, SN: 12345678, MAC: 00:1A:2B:3C:4D:5E, IP: 192.168.1.100, FW: 2.5.1
Config: 00001, Table: 00002, Layout: 00003, Exception: 0, PLC: 192.168.1.10
0, 0.000000, 0.123
1, 0.000039, 0.456
2, 0.000078, -0.789
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rd2', delete=False) as f:
            f.write(test_data)
            f.flush()
            parser = RD2Parser(f.name)
            result = parser.parse()
        self.assertEqual(result['metadata']['turbine_id'], 'WTG06')
        self.assertEqual(result['metadata']['sensor_name'], 'SENSOR_01_LOW_W')
        self.assertEqual(len(result['values']), 3)

class TestVibrationAnalyzer(unittest.TestCase):
    def test_rms_calculation(self):
        analyzer = VibrationAnalyzer()
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = analyzer.calculate_rms(values, window_size=3)
        expected_rms = np.sqrt(np.mean(values ** 2))
        self.assertAlmostEqual(result['total_rms'], expected_rms, places=5)
    
    def test_zone_determination(self):
        analyzer = VibrationAnalyzer()
        self.assertEqual(analyzer.determine_zone(1.5), 'A')
        self.assertEqual(analyzer.determine_zone(3.0), 'B')
        self.assertEqual(analyzer.determine_zone(6.0), 'C')
        self.assertEqual(analyzer.determine_zone(9.0), 'D')
    
    def test_fft_spectrum(self):
        analyzer = VibrationAnalyzer()
        sampling_freq = 1000
        t = np.linspace(0, 1.0, sampling_freq, False)
        values = np.sin(2 * np.pi * 50 * t)
        freqs, amps = analyzer.calculate_spectrum(values, sampling_freq)
        self.assertEqual(len(freqs), len(amps))
        self.assertGreater(len(freqs), 0)

class TestProcessRD2File(unittest.TestCase):
    def test_full_processing(self):
        test_data = """00001, 2024-01-15 10:30:45, WTG06, SMP12C-001, SENSOR_01_LOW_W
0.001 s, 25600 Hz, 131072 samples, 00001, 5.120 s
1500 RPM, 2500 KW, 12.5 m/s, 00001234, 50000.0 kWh
Device: SMP12C, SN: 12345678, MAC: 00:1A:2B:3C:4D:5E, IP: 192.168.1.100, FW: 2.5.1
Config: 00001, Table: 00002, Layout: 00003, Exception: 0, PLC: 192.168.1.10
"""
        for i in range(100):
            test_data += str(i) + ', ' + str(i * 0.000039) + ', ' + str(np.sin(i * 0.1) * 0.5) + '\n'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rd2', delete=False) as f:
            f.write(test_data)
            f.flush()
            result = process_rd2_file(f.name)
        self.assertIn('metadata', result)
        self.assertIn('rms', result)
        self.assertIn('spectrum', result)
        self.assertIn('zone', result)
        self.assertEqual(result['metadata']['turbine_id'], 'WTG06')

if __name__ == '__main__':
    unittest.main()
