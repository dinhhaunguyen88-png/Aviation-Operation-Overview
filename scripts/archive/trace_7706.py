from data_processor import DataProcessor
import json

dp = DataProcessor()

def find_7706():
    print("--- Searching for Flight 7706 ---")
    res = dp.supabase.table('flights').select('*').eq('flight_number', '7706').execute()
    if not res.data:
        print("Flight 7706 not found in 'flights' table.")
    else:
        print(f"Found {len(res.data)} records for 7706:")
        for f in res.data:
            print(f"ID: {f['id']}, Date: {f['flight_date']}, Dep: {f['departure']}, STD: {f['std']}")

if __name__ == "__main__":
    find_7706()
