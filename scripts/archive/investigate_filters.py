from data_processor import DataProcessor, filter_operational_flights
from datetime import date, timedelta

dp = DataProcessor()
target_date = date(2026, 2, 9)

def test_filtering():
    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    
    # Fetch all flights for 3 days
    all_f = []
    for d in [prev_date, target_date, next_date]:
        res = dp.supabase.table("flights").select("*").eq("flight_date", d.isoformat()).execute()
        all_f.extend(res.data)
        
    print(f"Total raw flights in 3-day window: {len(all_f)}")
    
    # 1. Current logic (with carrier code check)
    ops_current = filter_operational_flights(all_f, target_date)
    print(f"Current Filtered Count: {len(ops_current)}")
    
    # 2. Logic without carrier_code check
    def filter_no_carrier_check(flight_data, target_date):
        from airport_timezones import get_airport_timezone
        from datetime import datetime
        target_date_str = target_date.isoformat()
        next_date_str = (target_date + timedelta(days=1)).isoformat()
        prev_date_str = (target_date - timedelta(days=1)).isoformat()
        
        ops_flights = []
        for flight in flight_data:
            std_str = flight.get("std", "")
            dep_airport = flight.get("departure", "")
            f_date = flight.get("flight_date")
            flight_date_str = f_date.isoformat() if hasattr(f_date, 'isoformat') else f_date
            
            if std_str and ":" in std_str:
                try:
                    parts = std_str.split(":")
                    utc_hour = int(parts[0])
                    utc_min = int(parts[1]) if len(parts) > 1 else 0
                    tz_offset = get_airport_timezone(dep_airport)
                    
                    local_hour = utc_hour + int(tz_offset)
                    # Simple local shift
                    local_min = utc_min + int((tz_offset - int(tz_offset)) * 60)
                    if local_min >= 60:
                        local_min -= 60
                        local_hour += 1
                    
                    local_date = flight_date_str
                    if local_hour >= 24:
                        local_hour -= 24
                        if flight_date_str == prev_date_str: local_date = target_date_str
                        else: local_date = next_date_str
                    elif local_hour < 0:
                        local_hour += 24
                        if flight_date_str == target_date_str: local_date = prev_date_str
                        else: local_date = target_date_str
                        
                    if (local_date == target_date_str and local_hour >= 4) or \
                       (local_date == next_date_str and local_hour < 4):
                        ops_flights.append(flight)
                except: pass
        return ops_flights

    ops_relaxed = filter_no_carrier_check(all_f, target_date)
    # Deduplicate
    seen = set()
    unique = []
    for f in ops_relaxed:
        fn = f.get('flight_number', '').strip()
        dep = f.get('departure', '').strip()
        # Key on date + fn + dep
        key = (f['flight_date'], fn, dep)
        if key not in seen:
            seen.add(key)
            unique.append(f)
            
    print(f"Relaxed (No Carrier Check) Filtered Count: {len(unique)}")

if __name__ == "__main__":
    test_filtering()
