"""
Compare DayRepReport10Feb.csv (ground truth) vs System output.

DayRepReport shows flights for ops day 10/02/2026 (local times).
The CSV includes flights dated 10/02 AND early morning 11/02 (up to ~04:00 local).
Total per CSV footer: 520 records.

Goal: Parse CSV, then compare with what our system produces via API.
"""

import csv
import re
import json
import urllib.request
from collections import defaultdict

def parse_csv():
    """Parse DayRepReport10Feb.csv and return structured flights."""
    flights = []
    with open('DayRepReport10Feb.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 6:
                continue
            date_str = row[0].strip()
            # Skip header/footer rows
            if not re.match(r'\d{2}/\d{2}/\d{2}', date_str):
                continue
            
            flt_raw = row[1].strip()
            # Remove suffix marker " *" but keep the letter suffix
            flt_clean = flt_raw.replace(' *', '').strip()
            # Extract base number (without letter suffix like A, B)
            flt_base = re.sub(r'[A-Z]+$', '', flt_clean)
            flt_suffix = flt_clean[len(flt_base):]  # e.g. "A" or ""
            
            reg = row[2].strip()
            ac_type = row[3].strip()
            dep = row[4].strip()
            arr = row[5].strip()
            std_local = row[6].strip() if len(row) > 6 else ''
            sta_local = row[7].strip() if len(row) > 7 else ''
            
            flights.append({
                'date': date_str,
                'flt_raw': flt_raw,
                'flt_clean': flt_clean,
                'flt_base': flt_base,
                'flt_suffix': flt_suffix,
                'reg': reg,
                'ac_type': ac_type,
                'dep': dep,
                'arr': arr,
                'std_local': std_local,
                'sta_local': sta_local,
            })
    
    return flights

def fetch_system_flights():
    """Fetch flights from system API for Feb 10."""
    try:
        r = urllib.request.urlopen('http://localhost:5000/api/flights?date=2026-02-10')
        data = json.loads(r.read().decode())
        return data.get('data', {}).get('flights', [])
    except Exception as e:
        print(f"ERROR: Cannot fetch from system API: {e}")
        print("Make sure the app is running on port 5000")
        return []

def main():
    print("=" * 90)
    print("📊 COMPARISON: DayRepReport10Feb.csv vs System API")
    print("=" * 90)
    
    # 1. Parse CSV
    csv_flights = parse_csv()
    csv_10feb = [f for f in csv_flights if f['date'] == '10/02/26']
    csv_11feb = [f for f in csv_flights if f['date'] == '11/02/26']
    
    print(f"\n📁 CSV Analysis:")
    print(f"  Total records:       {len(csv_flights)}")
    print(f"  Flights on 10/02:    {len(csv_10feb)}")
    print(f"  Flights on 11/02:    {len(csv_11feb)} (early morning, part of 10/02 ops day)")
    
    # Count flights with suffixes
    suffixed = [f for f in csv_flights if f['flt_suffix']]
    if suffixed:
        print(f"\n  ⚠️ Suffixed flights ({len(suffixed)}):")
        for sf in suffixed:
            print(f"    {sf['flt_clean']:>8} ({sf['date']}) {sf['dep']}->{sf['arr']} STD={sf['std_local']}")
    
    # Build CSV lookup: key = (base_flight_number, dep_airport)
    csv_lookup = {}
    for f in csv_flights:
        key = (f['flt_base'], f['dep'])
        csv_lookup[key] = f
        # Also add with suffix
        if f['flt_suffix']:
            key_full = (f['flt_clean'], f['dep'])
            csv_lookup[key_full] = f
    
    # 2. Fetch system flights
    sys_flights = fetch_system_flights()
    if not sys_flights:
        print("\n❌ No system flights available. Run the app first.")
        return
    
    print(f"\n🖥️ System Analysis:")
    print(f"  Total flights from API: {len(sys_flights)}")
    
    # 3. Compare: System flights that are IN CSV
    in_csv = []
    not_in_csv = []
    
    for sf in sys_flights:
        fn = sf.get('flight_number', '').strip()
        dep = sf.get('departure', '').strip()
        # Try exact match first, then base match
        fn_base = re.sub(r'[A-Z]+$', '', fn)
        
        if (fn, dep) in csv_lookup or (fn_base, dep) in csv_lookup:
            in_csv.append(sf)
        else:
            not_in_csv.append(sf)
    
    print(f"\n🔍 Matching Results:")
    print(f"  System flights IN CSV:     {len(in_csv)}")
    print(f"  System flights NOT in CSV: {len(not_in_csv)}")
    
    if not_in_csv:
        print(f"\n  ⚠️ System flights NOT found in DayRepReport ({len(not_in_csv)}):")
        print(f"  {'FLT':>8} {'DB_DATE':>12} {'DEP':>4} {'ARR':>4} {'STD_UTC':>8} {'LOCAL':>6} {'STATUS':>10} {'REG':>12}")
        print("  " + "-" * 75)
        for f in sorted(not_in_csv, key=lambda x: x.get('flight_number', '')):
            fn = f.get('flight_number', '')
            db_date = f.get('_original_db_date', f.get('flight_date', ''))
            dep = f.get('departure', '')
            arr = f.get('arrival', '')
            std = (f.get('std', '') or '')[:5]
            local = f.get('local_std', '') or ''
            status = f.get('status', '') or f.get('flight_status', '') or ''
            reg = f.get('aircraft_reg', '')
            print(f"  {fn:>8} {db_date:>12} {dep:>4} {arr:>4} {std:>8} {local:>6} {status:>10} {reg:>12}")
    
    # 4. Reverse check: CSV flights NOT in system
    sys_lookup = {}
    for sf in sys_flights:
        fn = sf.get('flight_number', '').strip()
        dep = sf.get('departure', '').strip()
        fn_base = re.sub(r'[A-Z]+$', '', fn)
        sys_lookup[(fn, dep)] = sf
        sys_lookup[(fn_base, dep)] = sf
    
    csv_not_in_sys = []
    for cf in csv_flights:
        fn = cf['flt_clean']
        fn_base = cf['flt_base']
        dep = cf['dep']
        if (fn, dep) not in sys_lookup and (fn_base, dep) not in sys_lookup:
            csv_not_in_sys.append(cf)
    
    if csv_not_in_sys:
        print(f"\n  ⚠️ CSV flights NOT found in System ({len(csv_not_in_sys)}):")
        print(f"  {'FLT':>8} {'DATE':>10} {'DEP':>4} {'ARR':>4} {'STD_LOCAL':>10} {'REG':>12}")
        print("  " + "-" * 60)
        for f in csv_not_in_sys:
            print(f"  {f['flt_clean']:>8} {f['date']:>10} {f['dep']:>4} {f['arr']:>4} {f['std_local']:>10} {f['reg']:>12}")
    
    # 5. Summary
    print(f"\n{'=' * 90}")
    print(f"📊 SUMMARY:")
    print(f"  CSV (Ground Truth):  {len(csv_flights)} flights for ops day 10/02")
    print(f"  System (API):        {len(sys_flights)} flights")
    print(f"  Difference:          {len(sys_flights) - len(csv_flights)} ({'+' if len(sys_flights) > len(csv_flights) else ''}{len(sys_flights) - len(csv_flights)})")
    print(f"{'=' * 90}")

if __name__ == '__main__':
    main()
