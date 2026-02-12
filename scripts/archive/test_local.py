from data_processor import DataProcessor
from datetime import date, timedelta

dp = DataProcessor()
target_date = date(2026, 2, 9)

def test_local_assumption():
    target_str = target_date.isoformat()
    next_str = (target_date + timedelta(days=1)).isoformat()
    
    # Fetch today and tomorrow
    res_today = dp.supabase.table("flights").select("*").eq("flight_date", target_str).execute()
    res_tomorrow = dp.supabase.table("flights").select("*").eq("flight_date", next_str).execute()
    
    all_f = res_today.data + res_tomorrow.data
    
    in_window = []
    
    for f in all_f:
        std = f.get("std", "")
        f_date = f.get("flight_date")
        
        if not std or ":" not in std: continue
        
        parts = std.split(":")
        h = int(parts[0])
        
        # ASSUMPTION: std is LOCAL hour
        l_date = f_date
        l_h = h
        
        if (l_date == target_str and l_h >= 4) or (l_date == next_str and l_h < 4):
            in_window.append(f)
            
    # Deduplicate
    seen = set()
    unique = []
    for f in in_window:
        key = (f['flight_date'], f['flight_number'], f['departure'])
        if key not in seen:
            seen.add(key)
            unique.append(f)
            
    print(f"Count with LOCAL assumption: {len(unique)}")
    
    # Let's count how many from today were BEFORE 04:00
    before = [f for f in res_today.data if int(f['std'].split(":")[0]) < 4]
    print(f"Flights on {target_str} before 04:00 local: {len(before)}")
    print(f"Today total: {len(res_today.data)}")
    print(f"Today after 04:00: {len(res_today.data) - len(before)}")

if __name__ == "__main__": test_local_assumption()
