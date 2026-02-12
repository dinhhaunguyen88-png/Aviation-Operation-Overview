import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import date, timedelta

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

today = date(2026, 2, 11)
targets = ["SL", "SCL", "NS", "SICK", "CSL"]

crew_tables = [
    "standby_records",
    "fact_roster",
    "aims_leg_members",
    "flight_crew",
    "crew_flight_hours"
]

print(f"=== Searching for {targets} across Crew Tables for {today} ===")

results_found = []

for table in crew_tables:
    try:
        # Determine the date column name
        date_col = "duty_date"
        if table == "standby_records":
            # For standby_records, we check if today is within the range
            query = supabase.table(table).select("*") \
                .lte("duty_start_date", today.isoformat()) \
                .gte("duty_end_date", today.isoformat())
        elif table == "fact_roster":
            query = supabase.table(table).select("*") \
                .gte("start_dt", f"{today.isoformat()}T00:00:00") \
                .lte("start_dt", f"{today.isoformat()}T23:59:59")
        elif table == "crew_flight_hours":
            query = supabase.table(table).select("*") \
                .eq("calculation_date", today.isoformat())
        else:
            # table in ["aims_leg_members", "flight_crew"]
            query = supabase.table(table).select("*") \
                .eq("flight_date", today.isoformat())
        
        res = query.execute()
        
        if res.data:
            print(f"\nChecking {len(res.data)} records in {table}...")
            for row in res.data:
                match = None
                for k, v in row.items():
                    if str(v).upper().strip() in targets:
                        match = (k, v)
                        break
                
                if match:
                    results_found.append({
                        "table": table,
                        "crew_id": row.get("crew_id"),
                        "crew_name": row.get("crew_name") or row.get("name"),
                        "field": match[0],
                        "value": match[1],
                        "full_row": row
                    })
    except Exception as e:
        print(f"Error checking {table}: {e}")

if results_found:
    print(f"\n=== FOUND {len(results_found)} RELEVANT RECORDS ===")
    for r in results_found:
        print(f"Table: {r['table']} | Crew: {r['crew_id']} ({r['crew_name']}) | Found '{r['value']}' in column '{r['field']}'")
else:
    print("\nNo records found with those indicators for today.")
    print("Checking if any exist on other dates...")
    for table in crew_tables:
        try:
            res = supabase.table(table).select("*").limit(5000).execute()
            if res.data:
                for row in res.data:
                    for k, v in row.items():
                        if str(v).upper().strip() in targets:
                            print(f"Found '{v}' in {table}.{k} for date {row.get('flight_date') or row.get('duty_start_date') or row.get('start_dt') or row.get('calculation_date')}")
        except Exception: pass
