"""
Deep analysis of the 15 phantom flights - understand their UTC STD 
and which ops day they truly belong to.

Key question: Are these flights that AIMS assigned to Feb 10 (UTC) date 
but their LOCAL departure is actually in Feb 11 ops window (04:00+ local)?
"""

import json
import urllib.request
import re
from datetime import datetime, date, timedelta

# Phantom flights from comparison
PHANTOM_FLIGHTS = {
    # (flight_number, dep) -> notes
    ('1120', 'SGN'): 'DB:Feb10 UTC:23:50 Local:06:50 -> Feb 11 local, belongs to Feb 11 ops',
    ('1121', 'HAN'): 'DB:Feb10 UTC:21:10 Local:04:10 -> Feb 11 local, belongs to Feb 11 ops',
    ('1123', 'HAN'): 'DB:Feb10 UTC:22:20 Local:05:20 -> Feb 11 local, belongs to Feb 11 ops',
    ('120', 'SGN'):  'DB:Feb10 UTC:22:30 Local:05:30 -> Feb 11 local, belongs to Feb 11 ops',
    ('1330', 'PQC'): 'DB:Feb10 UTC:23:50 Local:06:50 -> Feb 11 local, belongs to Feb 11 ops',
    ('1371', 'VCL'): 'DB:Feb10 UTC:21:30 Local:04:30 -> Feb 11 local, belongs to Feb 11 ops',
    ('1603', 'CXR'): 'DB:Feb10 UTC:21:10 Local:04:10 -> Feb 11 local, belongs to Feb 11 ops',
    ('167', 'HAN'):  'DB:Feb10 UTC:23:50 Local:06:50 -> Feb 11 local, belongs to Feb 11 ops',
    ('247', 'THD'):  'DB:Feb10 UTC:21:05 Local:04:05 -> Feb 11 local, belongs to Feb 11 ops',
    ('509', 'HAN'):  'DB:Feb10 UTC:22:25 Local:05:25 -> Feb 11 local, belongs to Feb 11 ops',
    ('623', 'DAD'):  'DB:Feb10 UTC:22:25 Local:05:25 -> Feb 11 local, belongs to Feb 11 ops',
    ('833', 'FUK'):  'DB:Feb10 UTC:23:55 Local:08:55 -> Feb 11 local (Japan), belongs to Feb 11 ops',
    # From Feb 9 crossovers  
    ('176', 'SGN'):  'DB:Feb09 UTC:23:50 Local:06:50 -> Feb 10 local, but Feb 10 ops or Feb 9?',
    ('871', 'TAE'):  'DB:Feb09 UTC:22:50 Local:07:50 -> Feb 10 local (Korea), which ops day?',
    ('989', 'PUS'):  'DB:Feb09 UTC:23:30 Local:08:30 -> Feb 10 local (Korea), which ops day?',
}

def main():
    # Fetch system flights
    r = urllib.request.urlopen('http://localhost:5000/api/flights?date=2026-02-10')
    data = json.loads(r.read().decode())
    flights = data.get('data', {}).get('flights', [])
    
    print("=" * 100)
    print("PHANTOM FLIGHTS DEEP ANALYSIS")
    print("=" * 100)
    
    # Category A: DB date=Feb10, local STD >= 04:00 on Feb 11 -> should be Feb 11 ops
    # Category B: DB date=Feb09, local STD >= 04:00 on Feb 10 -> could be Feb 10 ops (crossover)
    
    cat_a = []  # Feb 10 DB flights that belong to Feb 11 ops day
    cat_b = []  # Feb 9 crossovers
    
    for f in flights:
        fn = f.get('flight_number', '').strip()
        dep = f.get('departure', '').strip()
        
        if (fn, dep) in PHANTOM_FLIGHTS:
            db_date = f.get('_original_db_date', f.get('flight_date', ''))
            std_utc = (f.get('std', '') or '')[:5]
            local_std = f.get('local_std', '') or ''
            status = f.get('status', '') or f.get('flight_status', '') or ''
            reg = f.get('aircraft_reg', '')
            arr = f.get('arrival', '')
            
            # Parse local hour
            local_hour = int(local_std.split(':')[0]) if local_std and ':' in local_std else -1
            
            info = {
                'fn': fn, 'dep': dep, 'arr': arr,
                'db_date': db_date, 'std_utc': std_utc,
                'local_std': local_std, 'local_hour': local_hour,
                'status': status, 'reg': reg
            }
            
            if '2026-02-09' in db_date:
                cat_b.append(info)
            else:
                cat_a.append(info)
    
    print(f"\nCategory A: Feb 10 DB flights with local STD that belongs to Feb 11 ops day ({len(cat_a)}):")
    print(f"  These flights have flight_date=2026-02-10 in DB (UTC date)")
    print(f"  But their local STD is >= 04:00 on FEB 11 -> they belong to Feb 11 ops day")
    print(f"  {'FLT':>8} {'DEP':>4} {'ARR':>4} {'STD_UTC':>8} {'LOCAL':>6} {'STATUS':>10} {'REG':>12}")
    print("  " + "-" * 70)
    for f in sorted(cat_a, key=lambda x: x['std_utc']):
        print(f"  {f['fn']:>8} {f['dep']:>4} {f['arr']:>4} {f['std_utc']:>8} {f['local_std']:>6} {f['status']:>10} {f['reg']:>12}")
    
    print(f"\nCategory B: Feb 9 DB crossover flights ({len(cat_b)}):")
    print(f"  These flights have flight_date=2026-02-09 in DB")
    print(f"  Their local STD crosses into Feb 10 local time")
    print(f"  Question: Are they in the DayRepReport for Feb 9 or Feb 10?")
    print(f"  {'FLT':>8} {'DEP':>4} {'ARR':>4} {'STD_UTC':>8} {'LOCAL':>6} {'STATUS':>10} {'REG':>12}")
    print("  " + "-" * 70)
    for f in sorted(cat_b, key=lambda x: x['std_utc']):
        print(f"  {f['fn']:>8} {f['dep']:>4} {f['arr']:>4} {f['std_utc']:>8} {f['local_std']:>6} {f['status']:>10} {f['reg']:>12}")
    
    # Now check: for Cat B flights, their local STD is 06:50/07:50/08:30,
    # which is >= 04:00. So they belong to Feb 10 ops day.
    # BUT they are NOT in DayRepReport10Feb.csv!
    # This means DayRepReport assigned them to Feb 9 ops day instead.
    # CONCLUSION: The CSV report (DayRepReport) uses the ORIGINAL flight_date (UTC date column),
    # not the local departure date for ops day assignment.
    
    print(f"\n{'=' * 100}")
    print("CONCLUSION:")
    print(f"{'=' * 100}")
    print("""
The DayRepReport uses AIMS's own ops day assignment, NOT a simple local-time window.
In AIMS, FlightDetailsForPeriod returns flights by their SCHEDULED DATE in the system.

Category A (12 flights):
  - DB date = Feb 10 (AIMS assigned to Feb 10)
  - Local STD >= 04:00 on Feb 11
  - NOT in DayRepReport10Feb -> they belong to Feb 11 ops
  - THESE SHOULD BE EXCLUDED from Feb 10 count

Category B (3 flights): 
  - DB date = Feb 9 (AIMS assigned to Feb 9)
  - Local STD >= 04:00 on Feb 10
  - NOT in DayRepReport10Feb -> AIMS considers them Feb 9 ops
  - Current system INCLUDES them as Feb 10 ops (Rule 2 wrong too!)

Total phantom surplus: 12 (Cat A) + 3 (Cat B) = 15 extra flights
CSV also has 1 flight (7706 HAN->KHV) not in system = -1
Net difference: +16 (system) vs CSV

CORRECT FIX:
 - System should match DayRepReport = 520 flights
 - Need to match AIMS's own ops day logic, not our local-time Rule 1/2/3
    """)

if __name__ == '__main__':
    main()
