import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import date

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

today = "2026-02-11"

print(f"--- Data counts for {today} ---")

# 1. Flights
flts = sb.table("flights").select("*", count="exact").eq("flight_date", today).execute()
print(f"flights: {flts.count}")

# 2. Standby Records (where today is between start and end)
sby = sb.table("standby_records").select("*", count="exact").lte("duty_start_date", today).gte("duty_end_date", today).execute()
print(f"standby_records (active today): {sby.count}")

# 3. Fact Roster
roster = sb.table("fact_roster").select("*", count="exact").gte("start_dt", f"{today}T00:00:00").lte("start_dt", f"{today}T23:59:59").execute()
print(f"fact_roster: {roster.count}")

# 4. Leg Members
legs = sb.table("aims_leg_members").select("*", count="exact").eq("flight_date", today).execute()
print(f"aims_leg_members: {legs.count}")

# 5. Daily Crew Status
daily = sb.table("daily_crew_status").select("*", count="exact").eq("status_date", today).execute()
print(f"daily_crew_status: {daily.count}")

if legs.count > 0:
    print("\nSample from aims_leg_members:")
    for r in legs.data[:3]:
        print(f"  Crew: {r.get('crew_id')} | Duty: {r.get('duty_code')} | Pos: {r.get('position')}")

if roster.count > 0:
    print("\nSample from fact_roster types:")
    types = set(r.get("activity_type") for r in roster.data)
    print(f"  Activity Types: {types}")
