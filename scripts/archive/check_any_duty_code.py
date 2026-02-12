import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("=== Checking aims_leg_members for any populated duty_code ===")
try:
    # Get all records where duty_code is not null and not empty
    res = supabase.table("aims_leg_members").select("duty_code, flight_date, flight_number, crew_id").not_.is_("duty_code", "null").execute()
    
    if res.data:
        # Filter out empty strings if any
        actual_data = [r for r in res.data if str(r.get("duty_code")).strip()]
        if actual_data:
            print(f"Found {len(actual_data)} records with duty_code!")
            for r in actual_data[:20]:
                print(f"  Date: {r['flight_date']} | Crew: {r['crew_id']} | Duty: {r['duty_code']}")
        else:
            print("No records with non-empty duty_code.")
    else:
        print("No records with populated duty_code found.")
except Exception as e:
    print(f"Error: {e}")
