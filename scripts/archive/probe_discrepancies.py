from data_processor import DataProcessor
import json

dp = DataProcessor()

def probe_discrepancies():
    # 1. Check for cancellations in aims_flight_mod_log for Feb 9-10
    print("--- Searching aims_flight_mod_log for 176, 871, 989 (Feb 9-10) ---")
    try:
        res = dp.supabase.table('aims_flight_mod_log').select('*').in_('flight_number', ['176', '871', '989']).in_('flight_date', ['2026-02-09', '2026-02-10']).execute()
        if not res.data:
            print("No modification logs found for these flights on Feb 9-10.")
        else:
            for log in res.data:
                print(f"Flt: {log['flight_number']}, Date: {log['flight_date']}, Dep: {log['departure']}, Type: {log['modification_type']}")
    except Exception as e:
        print(f"Error querying aims_flight_mod_log: {e}")

    # 2. Check for 7706 and its charter status (Detailed)
    print("\n--- Searching for 7706 in 'aims_flights' table (Detailed) ---")
    res = dp.supabase.table('aims_flights').select('*').eq('flight_number', '7706').execute()
    if not res.data:
        print("Flight 7706 not found.")
    else:
        for f in res.data:
            print(f"ID: {f['id']}, Date: {f['flight_date']}, Dep: {f['departure']}, Arr: {f['arrival']}, Carrier: {f.get('carrier_code')}, Status: {f.get('flight_status')}")

if __name__ == "__main__":
    probe_discrepancies()
