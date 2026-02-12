import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# We can't easily list all tables via the public API without RPC or special permissions
# but we can try to guess based on common names or check the ones we know and look for hidden columns.

known_tables = [
    "crew_members",
    "crew_flight_hours",
    "standby_records",
    "fact_roster",
    "aims_leg_members",
    "flight_crew",
    "aims_flights",
    "fact_actuals",
    "etl_jobs",
    "airports"
]

print("=== Checking Schemas of Known Tables ===")
for table in known_tables:
    try:
        res = supabase.table(table).select("*").limit(1).execute()
        if res.data:
            cols = list(res.data[0].keys())
            print(f"Table: {table}")
            print(f"  Columns: {cols}")
        else:
            print(f"Table: {table} (No data to infer columns)")
    except Exception as e:
        print(f"Table: {table} (Error: {e})")

# Searching for SL, SCL, NS in any table that has data
targets = ["SL", "SCL", "NS"]
print("\n=== Searching for Indicators SL, SCL, NS ===")
for table in known_tables:
    try:
        # We can't search all columns easily, so we check the most likely ones
        res = supabase.table(table).select("*").limit(1000).execute()
        if res.data:
            found = False
            for row in res.data:
                for k, v in row.items():
                    if str(v).upper() in targets:
                        print(f"Found {v} in {table}.{k} for ID {row.get('crew_id') or row.get('id')}")
                        found = True
                        break
                if found: break
    except Exception:
        pass
