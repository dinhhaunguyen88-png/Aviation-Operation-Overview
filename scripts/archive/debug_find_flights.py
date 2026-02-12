from data_processor import DataProcessor
import json

dp = DataProcessor()

def find_flight(flight_number):
    print(f"--- Searching for Flight {flight_number} ---")
    res = dp.supabase.table('flights').select('*').eq('flight_number', flight_number).execute()
    if not res.data:
        print("No flights found in 'flights' table.")
    else:
        for f in res.data:
            print(json.dumps(f, indent=2))

if __name__ == "__main__":
    find_flight('7706')
    # Also find the extra ones to be sure
    find_flight('1330')
    find_flight('176')
    find_flight('833')
    find_flight('871')
    find_flight('989')
