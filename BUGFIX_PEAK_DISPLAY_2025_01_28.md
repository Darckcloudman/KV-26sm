# Исправление отображения всех 10 пиков на спектрах

## 📅 Дата: 2025-01-28

---

## ❌ Описание проблемы

**Проблема:**
- На спектрах отображались не все 10 пиков, которые указаны в таблице гармоник
- Некоторые пики пропускались из-за фильтра по амплитуде
- Нумерация на графиках не соответствовала номерам в таблице

**Причины:**
1. В методе `_add_peak_markers()` был фильтр: `if peak_amp < np.max(amplitude_data) * 0.05: continue`
2. Не передавались номера пиков из таблицы в графики
3. Нумерация на каждом графике начиналась с 1, а не соответствовала глобальной нумерации из таблицы

---

## ✅ Решение

### 1. Убран фильтр по амплитуде

**Было:**
```python
# Не отображаем слишком малые пики (менее 5% от максимума)
if peak_amp < np.max(amplitude_data) * 0.05:
    continue
```

**Стало:**
```python
# Отображаем все пики из списка
```

---

### 2. Добавлена передача номеров пиков

**SpectrumChart:**
```python
def set_data(
    self,
    freq_data: np.ndarray,
    amplitude_data: np.ndarray,
    peak_frequencies: list | None = None,
    peak_numbers: list | None = None  # ✅ НОВЫЙ параметр
) -> None:
```

**_add_peak_markers:**
```python
def _add_peak_markers(
    self,
    freq_data: np.ndarray,
    amplitude_data: np.ndarray,
    peak_frequencies: list,
    peak_numbers: list | None = None  # ✅ НОВЫЙ параметр
) -> None:
    # Если номера пиков не переданы, используем порядковые номера
    if peak_numbers is None or len(peak_numbers) == 0:
        peak_numbers = list(range(1, len(peak_frequencies) + 1))
    
    # Используем номер пика из таблицы
    peak_number = peak_numbers[i] if i < len(peak_numbers) else (i + 1)
    
    marker = BlinkingPeakMarker(
        ...,
        number=peak_number,  # ✅ Номер из таблицы
        ...
    )
```

---

### 3. Добавлено сохранение глобального номера пика

**AnalysisDataScreen:**
```python
def _update_harmonics_table(self, data):
    # ...
    
    # Добавляем глобальный номер пика (из таблицы)
    for idx, peak in enumerate(top_peaks):
        peak['global_number'] = idx + 1  # ✅ Сохраняем номер
    
    self._current_peaks = {
        'НЧ': [p for p in top_peaks if p['signal_type'] == 'НЧ'],
        'ВЧ': [p for p in top_peaks if p['signal_type'] == 'ВЧ'],
        'ВЧ(ф)': [p for p in top_peaks if p['signal_type'] == 'ВЧ(ф)'],
    }
```

---

### 4. Обновлена передача пиков на графики

**AnalysisDataScreen._update_spectrums:**
```python
# НЧ спектр
nch_peaks = self._current_peaks.get('НЧ', [])
peak_freqs = [p['frequency'] for p in nch_peaks]
peak_nums = [p['global_number'] for p in nch_peaks]  # ✅ Берём номер из таблицы

self.spec_acc_chart.set_data(
    freqs[mask], amps[mask],
    peak_frequencies=peak_freqs,
    peak_numbers=peak_nums  # ✅ Передаём номера
)
```

---

## 📝 Изменения в файлах

| Файл | Изменения |
|------|-----------|
| `kwf_prometheus/gui/charts/spectrum_chart.py` | Добавлен параметр `peak_numbers`, убран фильтр по амплитуде |
| `kwf_prometheus/gui/analysis_data_screen.py` | Добавлено сохранение `global_number`, передача номеров в графики |

---

## ✅ Результат

| Было | Стало |
|------|-------|
| ❌ Отображались не все пики | ✅ Отображаются все 10 пиков из таблицы |
| ❌ Нумерация начиналась с 1 на каждом графике | ✅ Нумерация соответствует таблице (1-10) |
| ❌ Фильтр отсеивал пики < 5% | ✅ Все пики видны |

---

## 🎯 Пример

**Таблица гармоник:**
```
Пик | Тип  | Частота | Амплитуда
----|------|---------|----------
 1  | НЧ   |  50.0   |  5.2
 2  | ВЧ   | 120.5   |  4.8
 3  | НЧ   | 100.0   |  3.1
 4  | ВЧ(ф)| 500.0   |  2.9
...
```

**На графиках:**
- **НЧ спектр:** Пики №1 (50 Гц) и №3 (100 Гц) с номерами 1 и 3
- **ВЧ спектр:** Пик №2 (120.5 Гц) с номером 2
- **ВЧ(ф) спектр:** Пик №4 (500 Гц) с номером 4

---

## ✅ Проверка

```powershell
cd D:\Coding\pyton_pro
python -c "from kwf_prometheus.gui.charts.spectrum_chart import SpectrumChart; print('OK')"
python -c "from kwf_prometheus.gui.analysis_data_screen import AnalysisDataScreen; print('OK')"
```

**Результат:** ✅ Все импорты работают корректно

---

**Статус:** ✅ Исправлено  
**Версия:** v1.4.1  
**Приложение:** Готово к тестированию
