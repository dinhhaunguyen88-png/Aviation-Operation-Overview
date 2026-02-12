from data_processor import DataProcessor, filter_operational_flights
from datetime import date, timedelta
from airport_timezones import get_airport_timezone

dp = DataProcessor()
target_date = date(2026, 2, 9)

def find_missing_from_492():
    res = dp.supabase.table("flights").select("*").eq("flight_date", target_date.isoformat()).execute()
    data_today = res.data
    
    res_tomorrow = dp.supabase.table("flights").select("*").eq("flight_date", (target_date + timedelta(days=1)).isoformat()).execute()
    data_tomorrow = res_tomorrow.data
    
    all_f = data_today + data_tomorrow
    
    target_str = target_date.isoformat()
    next_str = (target_date + timedelta(days=1)).isoformat()
    
    in_window = []
    others = []
    
    for f in all_f:
        std = f.get("std", "")
        dep = f.get("departure", "")
        f_date = f.get("flight_date")
        
        if not std or ":" not in std:
            others.append((f, "No STD"))
            continue
            
        h = int(std.split(":")[0])
        offset = get_airport_timezone(dep)
        local_h = h + int(offset)
        
        l_date = f_date
        if local_h >= 24:
            local_h -= 24
            if f_date == target_str: l_date = next_str
        elif local_h < 0:
            local_h += 24
            if f_date == next_str: l_date = target_str
        
        if (l_date == target_str and local_h >= 4) or (l_date == next_str and local_h < 4):
            in_window.append(f)
        else:
            others.append((f, f"Outside window: {l_date} {local_h}h"))

    print(f"In Window Unique: {len(set((f['flight_date'], f['flight_number'], f['departure']) for f in in_window))}")
    
    # Let's see the 'Others' from today
    today_others = [o for o in others if o[0]['flight_date'] == target_str]
    print(f"Today's flights outside window: {len(today_others)}")
    for f, reason in today_others[:10]:
        print(f"  {f['flight_number']} {f['departure']} {f['std']} -> {reason}")

if __name__ == "__main__": find_missing_from_492()
