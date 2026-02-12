"""Debug: Check if local_std/local_sta fields are populated in API response"""
import requests
from dotenv import load_dotenv
import os, json

load_dotenv()
key = os.getenv('SUPABASE_KEY', '')
r = requests.get('http://localhost:5000/api/flights?date=2026-02-12', headers={'X-API-Key': key})
d = r.json()
flights = d.get('data', {}).get('flights', [])

print(f"Total flights: {len(flights)}")

# Count local_std presence
with_local = sum(1 for f in flights if f.get('local_std'))
without_local = sum(1 for f in flights if not f.get('local_std'))
print(f"With local_std: {with_local}")
print(f"Without local_std: {without_local}")

# Count parse errors
errs = [f for f in flights if f.get('_parse_error')]
print(f"Parse errors: {len(errs)}")

# Check first 3 flights
for i, f in enumerate(flights[:5]):
    print(f"\nFlight {i}: {f.get('flight_number')}")
    print(f"  flight_date={f.get('flight_date')} _original_db_date={f.get('_original_db_date')}")
    print(f"  local_flight_date={f.get('local_flight_date')}")
    print(f"  std(UTC)={f.get('std')}  local_std={f.get('local_std')}")
    print(f"  sta(UTC)={f.get('sta')}  local_sta={f.get('local_sta')}")
    print(f"  atd(UTC)={f.get('atd')}  local_atd={f.get('local_atd')}")
    print(f"  ata(UTC)={f.get('ata')}  local_ata={f.get('local_ata')}")
    print(f"  dep={f.get('departure')} arr={f.get('arrival')}")
    print(f"  _is_ops_filtered={f.get('_is_ops_filtered')}")
