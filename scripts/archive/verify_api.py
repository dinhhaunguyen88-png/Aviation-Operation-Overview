import sys
import os
from datetime import date

# Add current dir to path
sys.path.append(os.getcwd())

import data_processor

def verify_api_data():
    print("Verifying API data for local time fields...")
    dp = data_processor.DataProcessor(data_source='AIMS')
    
    # Get summary for today (Feb 10 2026 based on screenshot)
    target_date = date(2026, 2, 10)
    
    # We need to mock the DB or just check if the function logic works
    # Actually, let's just test get_flights directly which returns the list for the table
    flights = dp.get_flights(target_date)
    
    if not flights:
        print("No flights found for this date. (Check if DB has data)")
        return
        
    f = flights[0]
    print(f"\nSample Flight: {f.get('flight_number')} from {f.get('departure')}")
    
    fields_to_check = ['local_std', 'local_sta', 'local_etd', 'local_eta', 'local_atd', 'local_ata', 'local_tkof', 'local_tdwn']
    
    missing = []
    for field in fields_to_check:
        if field in f:
            print(f"  [FOUND] {field}: {f[field]}")
        else:
            print(f"  [MISSING] {field}")
            missing.append(field)
            
    if not missing:
        print("\nSUCCESS: All local fields are present in the flight objects.")
    else:
        print(f"\nFAILURE: Missing fields: {missing}")

if __name__ == "__main__":
    verify_api_data()
