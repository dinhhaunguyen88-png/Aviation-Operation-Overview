"""Test UTC to Local conversion for Aircraft Operating Today"""
import os, sys
sys.path.insert(0, 'd:/Aviation-Operation-Overview')
os.chdir('d:/Aviation-Operation-Overview')

from dotenv import load_dotenv
load_dotenv()

from datetime import date
from data_processor import DataProcessor

dp = DataProcessor()
target_date = date(2026, 2, 9)

print("=" * 70)
print(f"Testing Aircraft Operating Today - Local Time Conversion")
print("=" * 70)

data = dp.get_aircraft_summary(target_date)
print(f"\nData type: {type(data)}")

# Handle both dict and list responses
aircraft_list = data.get('aircraft', data) if isinstance(data, dict) else data

print(f"Total aircraft: {len(aircraft_list) if isinstance(aircraft_list, list) else 'N/A'}")
print()
print(f"{'REG':<10} | {'TYPE':<6} | {'FIRST':<10} | {'LAST':<10} | {'STATUS':<8}")
print("-" * 60)

# Show first 15 aircraft
if isinstance(aircraft_list, list):
    for ac in aircraft_list[:15]:
        first = ac.get('first_flight', '-')
        last = ac.get('last_flight', '-')
        print(f"{ac.get('reg', '-'):<10} | {ac.get('type', '-'):<6} | {first:<10} | {last:<10} | {ac.get('status', '-'):<8}")
else:
    print(f"Unexpected data structure: {aircraft_list}")

print()
print("=" * 70)
print("Expect times to be in VN local (UTC+7):")
print("  - 00:25 UTC → 07:25 local")
print("  - 01:15 UTC → 08:15 local")
print("=" * 70)
