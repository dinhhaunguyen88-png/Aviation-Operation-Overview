"""Verify FTL crew list sorted by hours_28_day desc shows real data."""
import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('X_API_KEY') or os.getenv('SUPABASE_KEY', '')

# Test 1: Default sort (hours_28_day desc) - should show highest hours first
req = urllib.request.Request(
    'http://localhost:5000/api/crew?sort_by=hours_28_day&sort_order=desc&per_page=10',
    headers={'X-API-Key': key}
)
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print("=== TEST 1: Sort by 28D Hours DESC (top 10) ===")
print(f"Total crew: {d['data']['total']}")
print(f"Page: {d['data']['page']}")
for c in d['data']['crew']:
    ftl = c.get('crew_flight_hours', [{}])
    hrs = ftl[0].get('hours_28_day', 0) if ftl and ftl[0] else 0
    h12 = ftl[0].get('hours_12_month', 0) if ftl and ftl[0] else 0
    lvl = ftl[0].get('warning_level', '') if ftl and ftl[0] else ''
    print(f"  {c['crew_id']:>6} | {c.get('crew_name','')[:25]:25} | base={c.get('base','').strip():3} | 28d={hrs:6.1f} | 12m={h12:7.1f} | {lvl}")

# Test 2: Filter by base=SGN + sort by hours
print()
req2 = urllib.request.Request(
    'http://localhost:5000/api/crew?base=SGN&sort_by=hours_28_day&sort_order=desc&per_page=5',
    headers={'X-API-Key': key}
)
r2 = urllib.request.urlopen(req2)
d2 = json.loads(r2.read())
print(f"=== TEST 2: SGN + Sort by Hours (top 5) ===")
print(f"Total SGN crew with FTL: {d2['data']['total']}")
for c in d2['data']['crew']:
    ftl = c.get('crew_flight_hours', [{}])
    hrs = ftl[0].get('hours_28_day', 0) if ftl and ftl[0] else 0
    print(f"  {c['crew_id']:>6} | {c.get('crew_name','')[:25]:25} | 28d={hrs:.1f}")

# Test 3: Filter level=CRITICAL
print()
req3 = urllib.request.Request(
    'http://localhost:5000/api/crew?level=CRITICAL&sort_by=hours_28_day&sort_order=desc&per_page=5',
    headers={'X-API-Key': key}
)
r3 = urllib.request.urlopen(req3)
d3 = json.loads(r3.read())
print(f"=== TEST 3: CRITICAL Level (top 5) ===")
print(f"Total CRITICAL: {d3['data']['total']}")
for c in d3['data']['crew']:
    ftl = c.get('crew_flight_hours', [{}])
    hrs = ftl[0].get('hours_28_day', 0) if ftl and ftl[0] else 0
    lvl = ftl[0].get('warning_level', '') if ftl and ftl[0] else ''
    print(f"  {c['crew_id']:>6} | {c.get('crew_name','')[:25]:25} | 28d={hrs:.1f} | {lvl}")
