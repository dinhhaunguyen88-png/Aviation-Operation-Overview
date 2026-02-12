from data_processor import DataProcessor
import json

dp = DataProcessor()

def inspect_flights():
    # 1. Get sample columns for 'flights'
    print("--- Sample columns for 'flights' ---")
    res = dp.supabase.table('flights').select('*').limit(1).execute()
    if res.data:
        print(json.dumps(res.data[0], indent=2))
    
    # 2. Check status for 176, 871, 989 on Feb 9-10
    print("\n--- Status for 176, 871, 989 (Feb 9-10) ---")
    res = dp.supabase.table('flights').select('flight_number, flight_date, departure, status').in_('flight_number', ['176', '871', '989']).in_('flight_date', ['2026-02-09', '2026-02-10']).execute()
    for f in res.data:
        print(f"Flt: {f['flight_number']}, Date: {f['flight_date']}, Dep: {f['departure']}, Status: {f['status']}")

if __name__ == "__main__":
    inspect_flights()
