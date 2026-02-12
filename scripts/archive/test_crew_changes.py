import os, sys
sys.path.insert(0, ".")
from datetime import date
from aims_soap_client import AIMSSoapClient
from dotenv import load_dotenv

load_dotenv()
client = AIMSSoapClient()
client._ensure_connection()

today = date(2026, 2, 11)
dt = client._format_date(today)

print(f"Testing CrewScheduleChangesForPeriod for {today}...")

try:
    response = client.client.service.CrewScheduleChangesForPeriod(
        UN=client.username,
        PSW=client.password,
        FromDD=dt["DD"], FromMM=dt["MM"], FromYYYY=dt["YYYY"],
        ToDD=dt["DD"], TOMM=dt["MM"], TOYYYY=dt["YYYY"]
    )
    
    print("\nAPI Response Structure:")
    print(dir(response))
    
    # Try to find indicators in the response
    found = False
    for attr in [a for a in dir(response) if not a.startswith('_')]:
        val = getattr(response, attr)
        if val:
            print(f"{attr}: {type(val)}")
            if hasattr(val, '__len__') and len(val) > 0:
                print(f"  Count: {len(val)}")
                print(f"  Sample: {val[0]}")
            found = True
            
    if not found:
        print("No changes found in response.")

except Exception as e:
    print(f"Failed: {e}")
