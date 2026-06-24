from datetime import datetime, timedelta

now = datetime.now()
print(f"Сейчас: {now}")
print(f"280 дней назад: {now - timedelta(days=280)}")
print(f"400 дней назад: {now - timedelta(days=400)}")
print(f"420 дней назад (14 мес): {now - timedelta(days=420)}")
print(f"500 дней назад: {now - timedelta(days=500)}")
print(f"\nДата данных: 2025-09-01")
print(f"Разница в днях от сегодня: {(now - datetime(2025, 9, 1)).days}")
