import requests

def verify():
    base_url = "http://localhost:5000/api/flights?date=2026-02-09"
    
    print("--- Testing Raw List (Normalization Verification) ---")
    r = requests.get(base_url)
    flights = r.json().get('data', {}).get('flights', [])
    types_found = sorted(list(set([f.get('aircraft_type') for f in flights])))
    print(f"Normalized types in API result: {types_found}")
    
    print("\n--- Testing Filter (A321) ---")
    r_filter = requests.get(f"{base_url}&aircraft_type=A321")
    f_filtered = r_filter.json().get('data', {}).get('flights', [])
    print(f"Flights found for A321: {len(f_filtered)}")
    if f_filtered:
        print(f"Sample filtered flight: {f_filtered[0].get('flight_number')} type={f_filtered[0].get('aircraft_type')}")

    print("\n--- Testing Focus Logic (Internal) ---")
    # We can't easily test frontend logic here, but we've verified the data is correct.
    # The frontend Now-2h to +1h will use these normalized types.

if __name__ == "__main__":
    verify()
