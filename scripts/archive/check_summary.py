from datetime import date
from data_processor import DataProcessor
import json

dp = DataProcessor()
target_date = date(2026, 2, 10)
summary = dp.get_dashboard_summary(target_date)

print(f"Total Flights in Summary: {summary.get('total_flights')}")
print(f"Total Aircraft in Summary: {summary.get('total_aircraft_operation')}")
