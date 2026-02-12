import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

tables_to_check = {
    "standby_records": ["status"],
    "fact_roster": ["activity_type", "duty_code"],
    "aims_leg_members": ["duty_code", "position", "category"],
    "flight_crew": ["position"],
    "crew_flight_hours": ["warning_level"]
}

print("=== Unique Values for Potential Indicator Columns ===")

for table, columns in tables_to_check.items():
    print(f"\nTable: {table}")
    for col in columns:
        try:
            res = supabase.table(table).select(col).execute()
            if res.data:
                unique_vals = sorted(list(set(str(row.get(col)).strip() for row in res.data if row.get(col))))
                print(f"  Column '{col}': {unique_vals}")
            else:
                print(f"  Column '{col}': (No data)")
        except Exception as e:
            print(f"  Column '{col}': Error - {e}")

# Also check for any unknown tables
try:
    print("\n=== Checking for other crew-related tables ===")
    # This might fail depending on permissions but it's worth a try
    # We can use the rpc call if defined, but usually we just list what we've seen in logs.
except Exception: pass
