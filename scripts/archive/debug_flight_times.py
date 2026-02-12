import requests

def debug_flights():
    target_date = "2026-02-09"
    url = f"http://localhost:5000/api/flights?date={target_date}"
    r = requests.get(url)
    flights = r.json().get('data', {}).get('flights', [])
    
    # Target flights from screenshot: 185, 240, 865, 1628
    targets = ["185", "240", "865", "1628", "925", "122"]
    
    print(f"{'FLT':<6} | {'DATE':<12} | {'STD':<10} | {'DEP':<4} | {'ARR':<4} | {'STA':<10}")
    print("-" * 60)
    
    found_count = 0
    for f in flights:
        if f.get('flight_number') in targets:
            print(f"{f.get('flight_number'):<6} | {f.get('flight_date'):<12} | {f.get('std'):<10} | {f.get('departure'):<4} | {f.get('arrival'):<4} | {f.get('sta'):<10}")
            found_count += 1
            
    print(f"\nTotal flights in response: {len(flights)}")
    print(f"Target flights found: {found_count}")

if __name__ == "__main__":
    debug_flights()
