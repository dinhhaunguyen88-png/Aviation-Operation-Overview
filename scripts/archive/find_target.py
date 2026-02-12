from data_processor import DataProcessor
from datetime import date, timedelta
from airport_timezones import get_airport_timezone

dp = DataProcessor()
target_date = date(2026, 2, 9)

def find_target_precise():
    # 1. Fetch 3 days
    dates = [target_date - timedelta(days=1), target_date, target_date + timedelta(days=1)]
    all_f = []
    for d in dates:
        all_f.extend(dp.supabase.table("flights").select("*").eq("flight_date", d.isoformat()).execute().data)
    
    # 2. Group by (flight_date, flight_number, departure) to see raw unique across 3 days
    raw_unique = {}
    for f in all_f:
        key = (f['flight_date'], f['flight_number'], f['departure'])
        if key not in raw_unique:
            raw_unique[key] = f
            
    print(f"Unique flights across 3-day window in DB: {len(raw_unique)}")
    
    # 3. Apply operational window (04:00 today to 03:59 tomorrow)
    target_str = target_date.isoformat()
    next_str = (target_date + timedelta(days=1)).isoformat()
    prev_str = (target_date - timedelta(days=1)).isoformat()
    
    ops_candidate = []
    for key, f in raw_unique.items():
        std = f.get("std", "")
        dep = f.get("departure", "")
        f_date_str = f.get("flight_date")
        
        if not std or ":" not in std: continue
        
        h = int(std.split(":")[0])
        offset = get_airport_timezone(dep)
        local_h = h + int(offset)
        
        l_date = f_date_str
        if local_h >= 24:
            local_h -= 24
            if f_date_str == prev_str: l_date = target_str
            elif f_date_str == target_str: l_date = next_str
        elif local_h < 0:
            local_h += 24
            if f_date_str == target_str: l_date = prev_str
            elif f_date_str == next_str: l_date = target_str
            
        if (l_date == target_str and local_h >= 4) or \
           (l_date == next_str and local_h < 4):
            ops_candidate.append(f)
            
    print(f"Flights in operational window (04:00-03:59): {len(ops_candidate)}")
    
    # 4. What if the window is 00:00 to 23:59 NEXT day? No.
    # What if we just take ALL flights on Feb 9?
    unique_target_date = [f for key, f in raw_unique.items() if f['flight_date'] == target_str]
    print(f"Unique flights with flight_date == {target_str}: {len(unique_target_date)}")
    
    # Check if there are 10 cancelled ones
    # Total unique on Feb 9 is 492? 
    # Let's see: 502 total in DB for Feb 9.
    # If 10 are duplicates or cancelled...
    
if __name__ == "__main__": find_target_precise()
