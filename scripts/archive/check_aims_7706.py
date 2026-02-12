from data_processor import DataProcessor
import json

dp = DataProcessor()

def check_aims_7706():
    print("--- Checking aims_flights for 7706 ---")
    res = dp.supabase.table('aims_flights').select('*').eq('flight_number', '7706').execute()
    for f in res.data:
        print(f"Date: {f['flight_date']}, Flt: {f['flight_number']}, Dep: {f['departure']}, LegCD: {f.get('leg_code')}")

if __name__ == "__main__":
    check_aims_7706()
