"""
Deep investigation: Why 492 flights become 445?
Step 1: Count raw flights in database for 3-day window
Step 2: Count after filter_operational_flights
Step 3: Identify which flights are being filtered OUT
"""
import os, sys
sys.path.insert(0, 'd:/Aviation-Operation-Overview')
os.chdir('d:/Aviation-Operation-Overview')

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from datetime import date, timedelta
from data_processor import filter_operational_flights

# Connect to Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

target_date = date(2026, 2, 9)
prev_date = target_date - timedelta(days=1)
next_date = target_date + timedelta(days=1)

print("=" * 60)
print(f"INVESTIGATION: Missing Flights for {target_date}")
print("=" * 60)

# Step 1: Count raw flights in DB for each date
print("\n[STEP 1] Raw flights in database:")

all_flights = []
for d in [prev_date, target_date, next_date]:
    result = supabase.table("flights").select("*", count="exact").eq("flight_date", d.isoformat()).execute()
    count = result.count or len(result.data or [])
    all_flights.extend(result.data or [])
    print(f"  {d}: {count} flights")

print(f"\n  TOTAL raw flights (3-day window): {len(all_flights)}")

# Step 2: Apply filter_operational_flights
filtered = filter_operational_flights(all_flights, target_date)
print(f"\n[STEP 2] After filter_operational_flights: {len(filtered)} flights")
print(f"  -> DROPPED: {len(all_flights) - len(filtered)} flights")

# Step 3: Identify which flights were dropped
print("\n[STEP 3] Analyzing dropped flights...")

filtered_keys = set()
for f in filtered:
    fnum = f.get("flight_number", "")
    dep = f.get("departure", "")
    fdate = f.get("flight_date", "")
    fdate_str = fdate.isoformat() if hasattr(fdate, 'isoformat') else fdate
    filtered_keys.add((fdate_str, fnum, dep))

dropped = []
for f in all_flights:
    fnum = f.get("flight_number", "")
    dep = f.get("departure", "")
    fdate = f.get("flight_date", "")
    fdate_str = fdate.isoformat() if hasattr(fdate, 'isoformat') else fdate
    std = f.get("std", "")
    
    # Check if in filtered
    key = (target_date.isoformat(), fnum, dep)  # Note: filtered uses target_date
    if key not in filtered_keys:
        dropped.append({
            "flight_number": fnum,
            "departure": dep,
            "arrival": f.get("arrival", ""),
            "flight_date": fdate_str,
            "std": std
        })

print(f"\n  Dropped flights: {len(dropped)}")
print(f"\n  Sample dropped flights (first 20):")
print(f"  {'FLT':<8} | {'DEP':<4} | {'ARR':<4} | {'DATE':<12} | {'STD':<10}")
print("  " + "-" * 50)

for f in dropped[:20]:
    print(f"  {f['flight_number']:<8} | {f['departure']:<4} | {f['arrival']:<4} | {f['flight_date']:<12} | {f['std']:<10}")

# Step 4: Analyze why flights were dropped
print("\n[STEP 4] Reasons for dropping:")

# Check for flights with empty STD
no_std = [f for f in dropped if not f['std'] or ':' not in str(f['std'])]
print(f"  - No valid STD time: {len(no_std)}")

# Check flights from prev_date that might have been excluded  
prev_date_drops = [f for f in dropped if f['flight_date'] == prev_date.isoformat()]
target_date_drops = [f for f in dropped if f['flight_date'] == target_date.isoformat()]
next_date_drops = [f for f in dropped if f['flight_date'] == next_date.isoformat()]

print(f"  - From {prev_date}: {len(prev_date_drops)} dropped")
print(f"  - From {target_date}: {len(target_date_drops)} dropped")  
print(f"  - From {next_date}: {len(next_date_drops)} dropped")

# Show target_date drops specifically
if target_date_drops:
    print(f"\n  Target date drops (should NOT be dropped):")
    for f in target_date_drops[:15]:
        print(f"    {f['flight_number']:<8} | {f['departure']:<4} | {f['arrival']:<4} | STD={f['std']}")
