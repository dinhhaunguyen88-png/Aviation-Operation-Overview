from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

for fn, dep in [('176', 'SGN'), ('871', 'TAE'), ('989', 'PUS')]:
    r = sb.table("flights").select("flight_date,std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    print(f"{fn} {dep}: Feb10 records = {len(r.data or [])}")
    if r.data:
        for row in r.data:
            print(f"  flight_date={row['flight_date']} std={row['std']}")
