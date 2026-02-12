import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("=== Checking daily_crew_status ===")
try:
    res = supabase.table("daily_crew_status").select("*").limit(5000).execute()
    if res.data:
        print(f"Total entries: {len(res.data)}")
        unique_duty_codes = sorted(list(set(str(row.get("duty_code")).strip() for row in res.data if row.get("duty_code"))))
        print(f"Unique duty_codes: {unique_duty_codes}")
        
        targets = ["SL", "SCL", "NS", "CSL", "SICK"]
        found = [r for r in res.data if str(r.get("duty_code")).upper().strip() in targets]
        if found:
            print(f"\nFOUND {len(found)} SICK-RELATED ENTRIES in daily_crew_status:")
            for r in found[:10]:
                print(f"  Crew: {r.get('crew_id')} | Date: {r.get('status_date')} | Code: {r.get('duty_code')}")
        else:
            print("\nNo sick-related entries found in daily_crew_status.")
    else:
        print("Table daily_crew_status exists but is empty.")
except Exception as e:
    print(f"Error checking daily_crew_status: {e}")
