import requests
import json

# Test Dashboard for Feb 9th
url = "http://localhost:5000/api/dashboard/summary?date=2026-02-09"
print(f"Fetching (Feb 9th): {url}")

response = requests.get(url)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json().get("data", {})
    keys = ["total_flights", "total_crew", "total_block_hours",
            "total_completed_flights", "total_aircraft_operation",
            "otp_percentage", "total_pax", "data_source"]
    
    print("\n--- API METRICS ---")
    for key in keys:
        print(f"{key}: {data.get(key)}")
else:
    print("FAILED TO FETCH DATA")
