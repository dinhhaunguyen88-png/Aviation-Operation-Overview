import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

target_date = "2026-02-04"  # Date with known data in aims_leg_members

print(f"=== Deep Scanning aims_leg_members for {target_date} ===")
try:
    res = supabase.table("aims_leg_members").select("*").eq("flight_date", target_date).execute()
    if res.data:
        print(f"Total records for {target_date}: {len(res.data)}")
        
        targets = ["SL", "SCL", "NS", "CSL", "SICK"]
        
        all_found = []
        for row in res.data:
            for k, v in row.items():
                val_str = str(v).upper().strip()
                if val_str in targets:
                    all_found.append((k, v, row))
        
        if all_found:
            print(f"\nFOUND {len(all_found)} TARGET INDICATORS:")
            for k, v, r in all_found[:20]:
                print(f"  Field: {k} | Value: {v} | Crew: {r.get('crew_id')} | Flight: {r.get('flight_number')}")
        else:
            print("\nNo targets found in any field for this date.")
            
            # Show unique values for ALL string/status-like columns
            for col in res.data[0].keys():
                vals = set(str(r.get(col)).strip() for r in res.data if r.get(col))
                if len(vals) < 50:
                    print(f"  Unique values in '{col}': {sorted(list(vals))}")
    else:
        print(f"No records found for {target_date}.")
except Exception as e:
    print(f"Error: {e}")
