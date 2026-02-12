from data_processor import DataProcessor
from datetime import date
import json

dp = DataProcessor()

def verify_final_count():
    target_date = date(2026, 2, 10)
    print(f"--- Verifying dashboard summary for {target_date} ---")
    summary = dp.get_dashboard_summary(target_date)
    
    total_flights = summary.get('total_flights', 0)
    print(f"Total Flights: {total_flights}")
    
    ops_flights = dp.get_flights(target_date)
    # Compare with CSV
    import csv
    csv_flights = set()
    with open('DayRepReport10Feb.csv', 'r', encoding='utf-8') as f:
        # Skip garbage headers (2 lines, line 3 is header)
        for _ in range(2): next(f)
        reader = csv.DictReader(f)
        for row in reader:
            fn = str(row.get('FLT') or '').strip()
            dep = str(row.get('DEP') or '').strip()
            if not fn or not dep or fn == 'FLT': continue
            csv_flights.add((fn, dep))
    
    # SYSTEM DEDUPLICATION
    # Group by (base_flight_number, departure)
    groups = {}
    for f in ops_flights:
        fn_full = f['flight_number']
        # Handle suffixes like 1250A, 1250/SGN, etc.
        # Use regex or simple logic to get the numeric part
        import re
        match = re.search(r'(\d+)', fn_full)
        base_fn = match.group(1) if match else fn_full
        
        dep = f['departure']
        key = (base_fn, dep)
        
        if key not in groups:
            groups[key] = []
        groups[key].append(f)
    
    # Pick the best from each group
    deduped_flights = []
    for key, variants in groups.items():
        # Priority: suffix over no-suffix, ARRIVED over others
        best = variants[0]
        for v in variants[1:]:
            # Prefer ones with suffixes (A, B, etc.)
            if ('A' in v['flight_number'] or '/' in v['flight_number']) and not ('A' in best['flight_number'] or '/' in best['flight_number']):
                best = v
            # Prefer ARRIVED status
            elif v['status'] == 'ARRIVED' and best['status'] != 'ARRIVED':
                best = v
        deduped_flights.append(best)
    
    print(f"Original Filtered: {len(ops_flights)}")
    print(f"Deduped Filtered: {len(deduped_flights)}")
    print(f"CSV Total: {len(csv_flights)}")
    
    missing = csv_flights - set([(re.search(r'(\d+)', f['flight_number']).group(1) if re.search(r'(\d+)', f['flight_number']) else f['flight_number'], f['departure']) for f in deduped_flights])
    extra = set([(re.search(r'(\d+)', f['flight_number']).group(1) if re.search(r'(\d+)', f['flight_number']) else f['flight_number'], f['departure']) for f in deduped_flights]) - csv_flights
    
    print(f"Missing ({len(missing)}): {missing}")
    print(f"Extra ({len(extra)}): {extra}")

if __name__ == "__main__":
    verify_final_count()
