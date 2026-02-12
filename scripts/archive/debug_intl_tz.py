"""Check international flights with different timezones"""
import requests
from datetime import datetime

def check_intl_flights():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    data = r.json().get('data', {})
    flights = data.get('flights', [])
    
    print("=== International Flights (non-VN airports) ===\n")
    print(f"{'FLT':<8} | {'DEP':<4} | {'ARR':<4} | {'STD (UTC)':<10} | {'local_std':<10} | {'date':<12}")
    print("-" * 70)
    
    vn_airports = {'SGN', 'HAN', 'DAD', 'CXR', 'PQC', 'VCA', 'HPH', 'HUI', 'VCL', 'UIH', 
                   'TBB', 'PXU', 'VDO', 'VII', 'VKG', 'BMV', 'DLI', 'VCS', 'THD', 'VDH'}
    
    intl_count = 0
    for f in flights:
        dep = f.get('departure', '')
        arr = f.get('arrival', '')
        
        # Check if departure OR arrival is international
        if dep not in vn_airports or arr not in vn_airports:
            std = f.get('std', '')
            local_std = f.get('local_std', 'N/A')
            flight_date = f.get('flight_date', '')
            
            print(f"{f.get('flight_number'):<8} | {dep:<4} | {arr:<4} | {std:<10} | {local_std:<10} | {flight_date:<12}")
            intl_count += 1
            
            if intl_count >= 30:
                print("... (showing first 30)")
                break
    
    print(f"\nTotal international flights displayed: {intl_count}")
    
    # Check for flights where local_std is very different from STD (timezone issues)
    print("\n\n=== Checking timezone conversions (STD vs local_std) ===")
    print("Looking for potential issues where conversion seems wrong...")
    print()
    
    for f in flights[:100]:
        std = f.get('std', '')
        local_std = f.get('local_std', '')
        dep = f.get('departure', '')
        
        if std and local_std and ':' in std and ':' in local_std:
            std_h = int(std.split(':')[0])
            local_h = int(local_std.split(':')[0])
            
            # Calculate offset (should be within expected ranges)
            offset = local_h - std_h
            if offset < 0:
                offset += 24
            elif offset > 12:
                offset -= 24
                
            # VN airports should have +7h offset
            # Korea airports +9h, Japan +9h, etc.
            # Flag anything unexpected
            vn = dep in vn_airports
            expected_offset = 7 if vn else None
            
            if vn and abs(offset - 7) > 1:  # Allow 1 hour tolerance for DST
                print(f"ISSUE: {f.get('flight_number'):<8} | {dep} | STD={std} | local={local_std} | offset={offset}h (expected ~7h)")

if __name__ == "__main__":
    check_intl_flights()
