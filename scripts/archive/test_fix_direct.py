"""Direct test of filter_operational_flights after fix"""
import sys
sys.path.insert(0, 'd:/Aviation-Operation-Overview')

from datetime import date, datetime, timedelta
from data_processor import filter_operational_flights, get_airport_timezone

# Create mock flights including overnight ones
mock_flights = [
    # Regular daytime flight
    {"flight_number": "VN100", "departure": "SGN", "arrival": "HAN", "flight_date": "2026-02-09", "std": "02:00:00", "sta": "04:00:00"},  # UTC 02:00 = VN 09:00
    # Overnight flight (UTC 18:00 = VN 01:00 next day)
    {"flight_number": "VN200", "departure": "PVG", "arrival": "SGN", "flight_date": "2026-02-09", "std": "18:15:00", "sta": "22:45:00"},  # UTC 18:15 = local 02:15 (next day)
    # Another overnight
    {"flight_number": "VN300", "departure": "AMD", "arrival": "HAN", "flight_date": "2026-02-09", "std": "18:40:00", "sta": "01:10:00"},  # UTC 18:40 = local 00:10 (next day) for India arrival
]

def test_filter():
    target = date(2026, 2, 9)
    result = filter_operational_flights(mock_flights, target)
    
    print("=== Testing filter_operational_flights after fix ===")
    print(f"Input: {len(mock_flights)} flights")
    print(f"Output: {len(result)} flights")
    print()
    
    for f in result:
        print(f"FLT: {f.get('flight_number')}")
        print(f"  flight_date: {f.get('flight_date')} (should be 2026-02-09)")
        print(f"  local_flight_date: {f.get('local_flight_date', 'N/A')}")
        print(f"  local_std: {f.get('local_std')}")
        print()
        
        # Verify flight_date is target date
        if f.get('flight_date') != '2026-02-09':
            print(f"  [ERROR] flight_date should be 2026-02-09!")
        else:
            print(f"  [OK] flight_date is correct")

if __name__ == "__main__":
    test_filter()
