"""
Quick: call data_processor.get_flights() directly to check
whether the function returns 536 or 467.
"""
import sys
sys.path.insert(0, '.')
from datetime import date
from data_processor import DataProcessor

dp = DataProcessor()
flights = dp.get_flights(date(2026, 2, 10))
print(f"DataProcessor.get_flights() returned: {len(flights)} flights")

# Check if 185 HAN is in results
found = [f for f in flights if f.get('flight_number', '').strip() == '185' and f.get('departure', '').strip() == 'HAN']
print(f"Flight 185 HAN: {len(found)}")
for f in found:
    print(f"  DB date: {f.get('_original_db_date')}, flight_date: {f.get('flight_date')}, std: {f.get('std')}, local_std: {f.get('local_std')}")
