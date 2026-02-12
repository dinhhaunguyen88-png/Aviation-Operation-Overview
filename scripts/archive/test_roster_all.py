from aims_soap_client import AIMSSoapClient
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
client = AIMSSoapClient()

print("Testing GetCrewSchedule with ID=0...")
try:
    schedules = client.get_crew_schedule(date.today(), date.today(), crew_id="0")
    print(f"Result count: {len(schedules)}")
    if schedules:
        print(f"Sample: {schedules[0]}")
except Exception as e:
    print(f"Error: {e}")
