import os, sys
sys.path.insert(0, ".")
from datetime import date
from aims_soap_client import AIMSSoapClient
from dotenv import load_dotenv

load_dotenv()
client = AIMSSoapClient()

today = date(2026, 2, 11)
print(f"Testing get_crew_schedule with ID=0 for {today}...")

try:
    rosters = client.get_crew_schedule(today, today, crew_id="0")
    print(f"Success! Found {len(rosters)} roster entries.")
    if rosters:
        print(f"Sample: {rosters[0]}")
except Exception as e:
    print(f"Failed: {e}")
