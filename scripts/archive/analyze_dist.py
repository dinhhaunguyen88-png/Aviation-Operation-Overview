from data_processor import DataProcessor
from datetime import date, timedelta
from airport_timezones import get_airport_timezone

dp = DataProcessor()
target_date = date(2026, 2, 9)

def analyze_distribution():
    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    
    all_f = []
    for d in [prev_date, target_date, next_date]:
        res = dp.supabase.table("flights").select("*").eq("flight_date", d.isoformat()).execute()
        all_f.extend(res.data)
        
    print(f"Total flights fetched: {len(all_f)}")
    target_str = target_date.isoformat()
    next_str = next_date.isoformat()
    prev_str = prev_date.isoformat()
    
    in_window = []
    before_window = [] # 00:00 - 03:59 on target_date
    after_window = [] # 04:00+ on next_date
    
    for f in all_f:
        std = f.get("std", "")
        dep = f.get("departure", "")
        f_date = f.get("flight_date")
        f_date_str = f_date.isoformat() if hasattr(f_date, 'isoformat') else f_date
        
        if not std or ":" not in std: continue
        
        parts = std.split(":")
        h = int(parts[0])
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
            
        if l_date == target_str:
            if local_h < 4:
                before_window.append(f)
            else:
                in_window.append(f)
        elif l_date == next_str:
            if local_h < 4:
                in_window.append(f)
            else:
                after_window.append(f)

    # Deduplicate in_window
    seen = set()
    unique_in = []
    for f in in_window:
        key = (f['flight_date'], f['flight_number'], f['departure'])
        if key not in seen:
            seen.add(key)
            unique_in.append(f)

    print(f"Flights in target operational window (04:00 {target_str} to 03:59 {next_str}): {len(unique_in)}")
    print(f"Flights before window (00:00-03:59 {target_str}): {len(before_window)}")
    print(f"Flights after window (04:00+ {next_str}): {len(after_window)}")
    
    # If count is still 445, let's see why it's not 492.
    # Total flights on Feb 9 in DB: 502.
    # If 492 is correct, then only 10 flights should be outside the window.
    
if __name__ == "__main__": analyze_distribution()
