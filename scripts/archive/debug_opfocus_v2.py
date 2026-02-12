"""Debug to check ALL flights sorted by local_std - simulating what frontend sees"""
import requests
from datetime import datetime

def full_flight_analysis():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    data = r.json().get('data', {})
    flights = data.get('flights', [])
    
    now = datetime.now()
    print(f"=== Operation Focus Analysis ===")
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Total flights from API: {len(flights)}")
    print()
    
    # Parse all flights like frontend does
    parsed_flights = []
    for f in flights:
        flight_date = f.get('flight_date', '')
        local_std = f.get('local_std', f.get('std', ''))
        
        if not local_std or ':' not in local_std:
            continue
            
        try:
            time_parts = local_std.split(':')
            flight_dt = datetime.fromisoformat(flight_date)
            flight_dt = flight_dt.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            
            time_diff_ms = (flight_dt.timestamp() - now.timestamp()) * 1000
            
            parsed_flights.append({
                'flight_number': f.get('flight_number'),
                'departure': f.get('departure'),
                'arrival': f.get('arrival'),
                'local_std': local_std,
                'flight_date': flight_date,
                '_flightTime': flight_dt,
                '_timeDiff': time_diff_ms
            })
        except Exception as e:
            pass
            
    # Simulate "Operation Focus" logic from dashboard.js lines 303-330
    now_ts = now.timestamp() * 1000  # JS uses milliseconds
    two_hours_ago_ms = now_ts - (2 * 60 * 60 * 1000)
    one_hour_hence_ms = now_ts + (1 * 60 * 60 * 1000)
    
    # Filter window flights
    focus_flights = [f for f in parsed_flights 
                     if f['_flightTime'].timestamp()*1000 >= two_hours_ago_ms 
                     and f['_flightTime'].timestamp()*1000 <= one_hour_hence_ms]
    
    print(f"Window: {datetime.fromtimestamp(two_hours_ago_ms/1000).strftime('%H:%M')} to {datetime.fromtimestamp(one_hour_hence_ms/1000).strftime('%H:%M')}")
    print(f"Flights in -2h to +1h window: {len(focus_flights)}")
    print()
    
    if len(focus_flights) < 15:
        # Sparse window - take 30 closest to now, sorted by time
        print("Sparse window - taking 30 closest flights")
        display_flights = sorted(parsed_flights, key=lambda x: abs(x['_timeDiff']))[:30]
        display_flights = sorted(display_flights, key=lambda x: x['_flightTime'])
    else:
        if len(focus_flights) > 50:
            # Too busy - take 40 closest
            print(f"Busy window ({len(focus_flights)} flights) - limiting to 40")
            display_flights = sorted(focus_flights, key=lambda x: abs(x['_timeDiff']))[:40]
            display_flights = sorted(display_flights, key=lambda x: x['_flightTime'])
        else:
            display_flights = sorted(focus_flights, key=lambda x: x['_flightTime'])
    
    print(f"\n=== What frontend SHOULD show ({len(display_flights)} flights) ===")
    print(f"{'#':<3} | {'FLT':<8} | {'DEP':<4} | {'ARR':<4} | {'Local STD':<9} | {'Diff (min)':<12}")
    print("-" * 60)
    
    for i, f in enumerate(display_flights[:30], 1):
        diff_mins = f['_timeDiff'] / 1000 / 60
        sign = "+" if diff_mins > 0 else ""
        print(f"{i:<3} | {f['flight_number']:<8} | {f['departure']:<4} | {f['arrival']:<4} | {f['local_std']:<9} | {sign}{diff_mins:.0f}")
    
    # Key check: Are flights sorted correctly by STD?
    print("\n=== Sanity Check: Are flights in chronological order? ===")
    sorted_correctly = True
    prev_time = None
    for f in display_flights:
        if prev_time and f['_flightTime'] < prev_time:
            print(f"OUT OF ORDER: {f['flight_number']} at {f['local_std']} comes BEFORE previous flight!")
            sorted_correctly = False
        prev_time = f['_flightTime']
    
    if sorted_correctly:
        print("✓ All flights are in chronological order")
    else:
        print("✗ Some flights are OUT OF ORDER!")

if __name__ == "__main__":
    full_flight_analysis()
