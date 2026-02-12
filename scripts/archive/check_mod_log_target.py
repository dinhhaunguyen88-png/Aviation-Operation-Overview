from data_processor import DataProcessor
import json

dp = DataProcessor()

def check_mod_log_target():
    print("--- Checking aims_flight_mod_log for 176, 871, 989 on Feb 9 ---")
    res = dp.supabase.table('aims_flight_mod_log').select('*').in_('flight_number', ['176', '871', '989']).eq('flight_date', '2026-02-09').execute()
    if not res.data:
        print("No dynamic deletions found for Feb 9.")
    else:
        for log in res.data:
            print(f"Flt: {log['flight_number']}, Date: {log['flight_date']}, Dep: {log['departure']}, Type: {log['modification_type']}")

if __name__ == "__main__":
    check_mod_log_target()
