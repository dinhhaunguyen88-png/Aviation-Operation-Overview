import requests

def check_flights():
    url = "http://localhost:5000/api/flights?date=2026-02-09"
    try:
        response = requests.get(url)
        data = response.json().get('data', {}).get('flights', [])
        
        print(f"Total flights found: {len(data)}")
        icn_flights = [f for f in data if f.get('departure') == 'ICN' or f.get('arrival') == 'ICN']
        
        if not icn_flights:
            print("No ICN flights found for Feb 9th.")
            # Let's show first 3 flights anyway to see the format
            icn_flights = data[:3]
            
        print(f"{'FLT':<6} | {'DEP':<4} | {'ARR':<4} | {'STD':<6} | {'STA':<6}")
        print("-" * 35)
        for f in icn_flights:
            print(f"{f.get('flight_number'):<6} | {f.get('departure'):<4} | {f.get('arrival'):<4} | {f.get('std'):<6} | {f.get('sta'):<6}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_flights()
