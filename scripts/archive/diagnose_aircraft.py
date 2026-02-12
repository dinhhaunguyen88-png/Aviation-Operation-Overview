import requests
import json

url = "http://localhost:5000/api/aircraft/daily-summary?date=2026-02-09"
print(f"Fetching: {url}")

response = requests.get(url)
if response.status_code == 200:
    data = response.json().get("data", {})
    aircraft = data.get("aircraft", [])
    
    print(f"\nTotal Aircraft: {data.get('total')}")
    print(f"{'Reg':<10} | {'Type':<6} | {'Flights':<8} | {'Range (First -> Last)':<20}")
    print("-" * 55)
    
    for ac in aircraft[:15]:  # Show first 15
        print(f"{ac['reg']:<10} | {ac['type']:<6} | {ac['flight_count']:<8} | {ac['first_flight']} -> {ac['last_flight']}")
else:
    print(f"FAILED: {response.status_code}")
