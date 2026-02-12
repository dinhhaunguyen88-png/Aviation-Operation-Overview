"""
Check: what flight_date do the 53 missing flights have in DB?
If they have flight_date=2026-02-09, they are prev-date and our new Rule 2 excluded them.
If they have flight_date=2026-02-10, it's a different issue.
"""
import json, urllib.request

# Fetch ALL raw flights from DB for Feb 9, 10, 11 (the 3-day window)
missing_flights_csv = [
    ('105','HAN'), ('270','SGN'), ('1370','SGN'), ('244','SGN'), ('185','HAN'),
    ('869','PUS'), ('969','PUS'), ('963','ICN'), ('302','SGN'), ('925','ICN'),
    ('981','PUS'), ('1306','SGN'), ('1307','HUI'), ('621','DAD'), ('835','ICN'),
    ('837','ICN'), ('122','SGN'), ('620','SGN'), ('879','ICN'), ('1628','SGN'),
    ('991','PUS'), ('443','HAN'), ('260','SGN'), ('421','HAN'), ('491','HAN'),
    ('1279','HPH'), ('356','SGN'), ('524','DAD'), ('813','SGN'), ('823','NRT'),
    ('179','HAN'), ('461','HAN'), ('959','FUK'), ('1621','DAD'), ('380','SGN'),
    ('181','HAN'), ('502','DAD'), ('1302','SGN'), ('1372','SGN'), ('1373','VCL'),
    ('717','DAD'), ('401','HAN'), ('977','ICN'), ('126','SGN'), ('952','HAN'),
    ('865','ICN'), ('503','HAN'), ('841','TPE'), ('124','SGN'), ('773','HAN'),
]

# Use the dashboard API to get flights - but that goes through filter.
# Instead, let's query Supabase directly or check the raw API.
# Actually let's use /api/flights which returns filtered flights.
# Let me instead check what dates these flights have by looking at the UNFILTERED data.

# The /api/flights endpoint applies filter_operational_flights.
# We need to check the raw DB. Let's write a quick script that checks.
from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

# Check Feb 9 flights
for flt_num, dep in missing_flights_csv[:10]:  # Check first 10
    # Query DB for this flight on Feb 9, 10, 11
    for d in ['2026-02-09', '2026-02-10', '2026-02-11']:
        result = sb.table("flights").select("flight_date,flight_number,departure,std").eq("flight_number", flt_num).eq("departure", dep).eq("flight_date", d).execute()
        if result.data:
            for r in result.data:
                print(f"  FLT {flt_num:>6} DEP={dep:>4} DB_DATE={r['flight_date']} STD_UTC={r.get('std','')}")

print("\nSummary: Checking if missing flights are on Feb 9...")
feb9_count = 0
feb10_count = 0
for flt_num, dep in missing_flights_csv:
    r9 = sb.table("flights").select("flight_date").eq("flight_number", flt_num).eq("departure", dep).eq("flight_date", "2026-02-09").execute()
    r10 = sb.table("flights").select("flight_date").eq("flight_number", flt_num).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    if r9.data:
        feb9_count += 1
    elif r10.data:
        feb10_count += 1
    else:
        print(f"  NOT FOUND: {flt_num} {dep}")

print(f"\nMissing flights on Feb 9 in DB: {feb9_count}")
print(f"Missing flights on Feb 10 in DB: {feb10_count}")
