from data_processor import DataProcessor
import json

dp = DataProcessor()

def verify_cancellations():
    print("--- Verifying status for 176, 871, 989 on Feb 10 ---")
    res = dp.supabase.table('flights').select('flight_number, flight_date, departure, status').in_('flight_number', ['176/SGN', '871/TAE', '989/PUS']).eq('flight_date', '2026-02-10').execute()
    if not res.data:
        # Check without suffix too just in case
        res = dp.supabase.table('flights').select('flight_number, flight_date, departure, status').in_('flight_number', ['176', '871', '989']).eq('flight_date', '2026-02-10').execute()
    
    for f in res.data:
        print(f"Flt: {f['flight_number']}, Date: {f['flight_date']}, Dep: {f['departure']}, Status: {f['status']}")

if __name__ == "__main__":
    verify_cancellations()
