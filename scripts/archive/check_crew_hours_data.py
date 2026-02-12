import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

today = "2026-02-11"
res = sb.table("crew_flight_hours").select("*", count="exact").eq("calculation_date", today).execute()
print(f"crew_flight_hours count for {today}: {res.count}")
if res.data:
    print(f"Sample record keys: {res.data[0].keys()}")
