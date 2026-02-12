"""
Quick check: How many flights does DB have for Feb 9, 10, 11?
And specifically check flight 185 HAN departure.
"""
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

for d in ['2026-02-09', '2026-02-10', '2026-02-11']:
    result = sb.table("flights").select("id", count="exact").eq("flight_date", d).execute()
    print(f"  {d}: {result.count} flights in DB")

# Check flight 185 on Feb 10
print("\nFlight 185 HAN on Feb 10:")
r = sb.table("flights").select("flight_date,flight_number,departure,std,arrival").eq("flight_number", "185").eq("departure", "HAN").eq("flight_date", "2026-02-10").execute()
for row in r.data:
    print(f"  {row}")

# Check if it's being fetched by get_flights
# The issue might be that flight 185 on Feb 10 has STD=22:10 UTC
# and filter Rule 1 includes it, but dedup removes it because 
# the key (target_date, "185", "HAN") was already seen from the Feb 9 copy...
# Wait - but we disabled Rule 2, so Feb 9 copy should NOT be included!

# Let me check: is the Feb 10 copy even being fed to filter_operational_flights?
print("\nFlight 185 HAN on Feb 9:")
r9 = sb.table("flights").select("flight_date,flight_number,departure,std").eq("flight_number", "185").eq("departure", "HAN").eq("flight_date", "2026-02-09").execute()
for row in r9.data:
    print(f"  {row}")

# Real question: When get_flights() fetches for target=Feb 10,
# it fetches prev=Feb9, target=Feb10, next=Feb11
# Flight 185 exists on BOTH Feb 9 and Feb 10
# Rule 2 now excludes Feb 9 copy -> good
# Rule 1 includes Feb 10 copy -> should be there
# Unless there's an issue with dedup key collision

# Let me check the full pipeline manually
from data_processor import filter_operational_flights
from datetime import date

# Simulate: get all flights for Feb 9+10+11
all_flights = []
for d in ['2026-02-09', '2026-02-10', '2026-02-11']:
    result = sb.table("flights").select("*").eq("flight_date", d).execute()
    all_flights.extend(result.data or [])

print(f"\nTotal raw flights (3 days): {len(all_flights)}")

# Now filter
ops = filter_operational_flights(all_flights, date(2026, 2, 10))
print(f"After filter: {len(ops)}")

# Check if 185 is in results
found = [f for f in ops if f.get('flight_number', '').strip() == '185' and f.get('departure', '').strip() == 'HAN']
print(f"\nFlight 185 HAN in results: {len(found)}")
for f in found:
    print(f"  DB date: {f.get('_original_db_date')}, flight_date: {f.get('flight_date')}, std: {f.get('std')}, local_std: {f.get('local_std')}")
