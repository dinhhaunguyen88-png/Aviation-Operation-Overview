"""Verify exact issue with late night flights"""
import os, sys
sys.path.insert(0, 'd:/Aviation-Operation-Overview')
os.chdir('d:/Aviation-Operation-Overview')

from datetime import date, datetime, timedelta
from airport_timezones import get_airport_timezone

# Test specific flight that was dropped
test_cases = [
    {"flight_number": "122", "departure": "SGN", "flight_date": "2026-02-09", "std": "22:20:00"},
    {"flight_number": "105", "departure": "HAN", "flight_date": "2026-02-09", "std": "23:45:00"},
    {"flight_number": "1306", "departure": "SGN", "flight_date": "2026-02-09", "std": "21:20:00"},
]

target_date = date(2026, 2, 9)
target_date_str = target_date.isoformat()
next_date_str = (target_date + timedelta(days=1)).isoformat()

print("Analyzing why these flights are dropped:")
print()

for flight in test_cases:
    std_str = flight["std"]
    dep_airport = flight["departure"]
    flight_date_str = flight["flight_date"]
    
    tz_offset = get_airport_timezone(dep_airport)
    
    # Parse UTC datetime
    utc_dt = datetime.combine(
        date.fromisoformat(flight_date_str),
        datetime.strptime(std_str[:5], "%H:%M").time()
    )
    
    # Convert to local station datetime
    local_dt = utc_dt + timedelta(hours=tz_offset)
    local_date_iso = local_dt.date().isoformat()
    local_hour = local_dt.hour
    
    # Current filter condition
    # Check if it falls in the 04:00 (target) to 03:59 (next) window
    passes_filter = (local_date_iso == target_date_str and local_hour >= 4) or \
                    (local_date_iso == next_date_str and local_hour < 4)
    
    print(f"Flight {flight['flight_number']} ({dep_airport}):")
    print(f"  STD (UTC):     {std_str}")
    print(f"  TZ offset:     +{tz_offset}h")
    print(f"  Local time:    {local_dt.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Local date:    {local_date_iso}")
    print(f"  Local hour:    {local_hour}")
    print(f"  Target date:   {target_date_str}")
    print(f"  Next date:     {next_date_str}")
    print(f"  Filter check:  (local_date={local_date_iso} == target AND hour>={local_hour}>=4) = {local_date_iso == target_date_str and local_hour >= 4}")
    print(f"                 (local_date={local_date_iso} == next AND hour={local_hour}<4) = {local_date_iso == next_date_str and local_hour < 4}")
    print(f"  PASSES FILTER: {passes_filter}")
    print()
    
print("=" * 60)
print("PROBLEM: Flights with STD 21:00-23:59 UTC = 04:00-06:59 local NEXT DAY")
print("         But filter requires local < 04:00 for next day to pass!")
print("=" * 60)
