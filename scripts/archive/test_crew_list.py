import os, sys
sys.path.insert(0, ".")
from datetime import date
from aims_soap_client import AIMSSoapClient
from dotenv import load_dotenv

load_dotenv()
client = AIMSSoapClient()

today = date(2026, 2, 11)
print(f"Testing get_crew_list for {today}...")

try:
    crew = client.get_crew_list(today, today)
    print(f"Success! Found {len(crew)} crew members.")
    if crew:
        print(f"Sample: {crew[0]}")
except Exception as e:
    print(f"Failed: {e}")
