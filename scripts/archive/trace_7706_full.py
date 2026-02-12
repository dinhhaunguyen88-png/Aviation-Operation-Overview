from data_processor import DataProcessor
import json

dp = DataProcessor()

def trace_discrepancies():
    print("--- Tracing 176, 871, 989 on Feb 10 ---")
    res = dp.supabase.table('flights').select('*').in_('flight_number', ['176/SGN', '871/TAE', '989/PUS']).eq('flight_date', '2026-02-10').execute()
    for f in res.data:
        print(f"Flt: {f['flight_number']}, Date: {f['flight_date']}, Dep: {f['departure']}, Std: {f.get('std')}, Status: {f.get('status')}")
    if not res.data:
        print("No records found for 7706.")
    else:
        for f in sorted(res.data, key=lambda x: (x['flight_date'], x.get('std', ''))):
            print(f"ID: {f['id']}, Date: {f['flight_date']}, Flt: {f['flight_number']}, Dep: {f['departure']}, Arr: {f['arrival']}, Std: {f.get('std')}, Status: {f.get('status')}, Source: {f.get('source')}")

if __name__ == "__main__":
    trace_discrepancies()
