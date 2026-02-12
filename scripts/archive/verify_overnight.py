"""Verify overnight flight fix"""
import requests
from datetime import datetime

def verify_overnight_fix():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    data = r.json().get('data', {})
    flights = data.get('flights', [])
    
    print("=== Verify Overnight Flight Fix ===")
    print(f"Total flights: {len(flights)}")
    print()
    
    # Check overnight flights (local_std between 00:00-03:59)
    overnight = []
    for f in flights:
        local_std = f.get('local_std', '')
        if local_std and ':' in local_std:
            h = int(local_std.split(':')[0])
            if h < 4:
                overnight.append(f)
    
    print(f"Overnight flights (local_std 00:00-03:59): {len(overnight)}")
    print()
    print(f"{'FLT':<8} | {'DEP':<4} | {'ARR':<4} | {'local_std':<10} | {'flight_date':<12} | {'local_flight_date':<15}")
    print("-" * 80)
    
    for f in overnight[:15]:
        print(f"{f.get('flight_number'):<8} | {f.get('departure'):<4} | {f.get('arrival'):<4} | {f.get('local_std'):<10} | {f.get('flight_date'):<12} | {f.get('local_flight_date', 'N/A'):<15}")
    
    # Verify that flight_date is target_date and local_flight_date is next day
    print()
    print("=== Verification ===")
    errors = 0
    for f in overnight:
        flight_date = f.get('flight_date', '')
        local_date = f.get('local_flight_date', '')
        
        if flight_date != target_date:
            print(f"ERROR: {f.get('flight_number')} has flight_date={flight_date}, expected {target_date}")
            errors += 1
        if local_date and local_date == target_date:
            print(f"WARN: {f.get('flight_number')} has local_flight_date={local_date} same as target (should be next day)")
            
    if errors == 0:
        print("[OK] All overnight flights have correct flight_date = target_date")
    else:
        print(f"[FAIL] {errors} errors found")

if __name__ == "__main__":
    verify_overnight_fix()
