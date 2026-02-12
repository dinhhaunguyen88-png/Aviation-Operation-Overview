"""Debug Operation Focus logic"""
import requests
from datetime import datetime

def debug_operation_focus():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    data = r.json().get('data', {})
    flights = data.get('flights', [])
    
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Total flights from API: {len(flights)}")
    print()
    
    # Operation Focus window: -2h to +1h from now
    two_hours_ago = now.timestamp() - (2 * 60 * 60)
    one_hour_hence = now.timestamp() + (1 * 60 * 60)
    
    print(f"Window: {datetime.fromtimestamp(two_hours_ago).strftime('%H:%M')} to {datetime.fromtimestamp(one_hour_hence).strftime('%H:%M')}")
    print()
    
    # Parse flight times like frontend does
    focus_flights = []
    for f in flights[:50]:  # Check first 50
        flight_date = f.get('flight_date', '')
        local_std = f.get('local_std', f.get('std', ''))
        
        if not local_std or ':' not in local_std:
            continue
            
        try:
            # This is what frontend does (problematic!)
            time_parts = local_std.split(':')
            flight_dt = datetime.fromisoformat(flight_date)
            flight_dt = flight_dt.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            
            time_diff_mins = (flight_dt.timestamp() - now.timestamp()) / 60
            
            # Is it in the -2h to +1h window?
            in_window = -120 <= time_diff_mins <= 60
            
            if len(focus_flights) < 10:
                print(f"FLT {f.get('flight_number'):<6} | date={flight_date} | local_std={local_std} | flight_dt={flight_dt} | diff_mins={time_diff_mins:+.0f} | in_window={in_window}")
                
            if in_window:
                focus_flights.append(f)
        except Exception as e:
            print(f"Error parsing {f.get('flight_number')}: {e}")
            
    print()
    print(f"Flights in Operation Focus window (-2h to +1h): {len(focus_flights)}")
    
    # Show sample of flight dates
    print("\n--- Sample flight_date values ---")
    dates = set()
    for f in flights[:100]:
        dates.add(f.get('flight_date'))
    for d in sorted(dates):
        print(f"  {d}")
        
    # Show what times the flights have
    print("\n--- STD distribution (first 20 flights) ---")
    for f in flights[:20]:
        print(f"{f.get('flight_number'):<6} | {f.get('flight_date')} | STD={f.get('std')} | local_std={f.get('local_std', 'N/A')}")

if __name__ == "__main__":
    debug_operation_focus()
