"""Final verification: Count unique flights for operational day"""
import os, sys
sys.path.insert(0, 'd:/Aviation-Operation-Overview')
os.chdir('d:/Aviation-Operation-Overview')

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from datetime import date, timedelta
from data_processor import filter_operational_flights

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

target_date = date(2026, 2, 9)
prev_date = target_date - timedelta(days=1)
next_date = target_date + timedelta(days=1)

# Fetch all flights
all_flights = []
for d in [prev_date, target_date, next_date]:
    result = supabase.table("flights").select("*").eq("flight_date", d.isoformat()).execute()
    all_flights.extend(result.data or [])

# Apply filter
filtered = filter_operational_flights(all_flights, target_date)

print("=" * 60)
print(f"FINAL VERIFICATION: Flight count for {target_date}")
print("=" * 60)
print(f"\nRaw flights in DB for {target_date}: {len([f for f in all_flights if f.get('flight_date') == target_date.isoformat()])}")
print(f"After filter_operational_flights: {len(filtered)}")

# Count unique by flight_number + departure
unique_keys = set()
for f in filtered:
    key = (f.get('flight_number', ''), f.get('departure', ''))
    unique_keys.add(key)
print(f"Unique (flight_number, departure) pairs: {len(unique_keys)}")

# Check for any duplicates
from collections import Counter
keys = [(f.get('flight_number', ''), f.get('departure', '')) for f in filtered]
duplicates = [(k, c) for k, c in Counter(keys).items() if c > 1]
if duplicates:
    print(f"\nDuplicates found: {len(duplicates)}")
    for (flt, dep), count in duplicates[:10]:
        print(f"  {flt} ({dep}): {count} times")
else:
    print("\nNo duplicates found!")
    
print(f"\n{'='*60}")
print(f"TOTAL FLIGHTS FOR API RESPONSE: {len(filtered)}")
print(f"{'='*60}")
