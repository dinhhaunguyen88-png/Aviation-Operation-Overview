import requests
from datetime import datetime, date

def verify_fix():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    data = r.json()
    # Check structure
    if 'data' in data:
        flights = data['data'].get('flights', [])
    else:
        flights = data.get('flights', [])
        
    print(f"Total flights for {target_date}: {len(flights)}")
    
    # Sort by local date and local time
    flights.sort(key=lambda x: (str(x.get('flight_date')), str(x.get('local_std') or '')))
    
    print(f"\n{'FLT':<6} | {'DEP':<4} | {'ARR':<4} | {'DATE':<12} | {'UTC STD':<10} | {'LOCAL STD':<10}")
    print("-" * 65)
    
    # Show first 15 (should start from 04:00 VN)
    for f in flights[:15]:
        flt = f.get('flight_number', '-')
        dep = f.get('departure', '-')
        arr = f.get('arrival', '-')
        fdt = f.get('flight_date', '-')
        std = f.get('std', '-')
        lst = f.get('local_std', '-')
        print(f"{flt:<6} | {dep:<4} | {arr:<4} | {fdt:<12} | {std:<10} | {lst:<10}")
        
    print("\n...\n")
    
    # Show last 10 (should end before 04:00 tomorrow)
    for f in flights[-10:]:
        flt = f.get('flight_number', '-')
        dep = f.get('departure', '-')
        arr = f.get('arrival', '-')
        fdt = f.get('flight_date', '-')
        std = f.get('std', '-')
        lst = f.get('local_std', '-')
        print(f"{flt:<6} | {dep:<4} | {arr:<4} | {fdt:<12} | {std:<10} | {lst:<10}")

if __name__ == "__main__":
    verify_fix()
