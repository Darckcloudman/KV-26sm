from datetime import datetime, timedelta

# Текущая дата
now = datetime.now()
print(f"Текущая дата: {now}")

# Дата 120 дней назад
start_date = now - timedelta(days=120)
print(f"120 дней назад: {start_date}")

# Дата наших данных
data_date = datetime(2025, 9, 1)
print(f"Дата данных: {data_date}")

# Проверка
if data_date >= start_date and data_date <= now:
    print("✓ Дата в диапазоне 120 дней")
else:
    print("✗ Дата ВНЕ диапазона 120 дней!")
    print(f"  Разница: {(now - data_date).days} дней назад")
