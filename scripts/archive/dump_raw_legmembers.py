import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from aims_soap_client import AIMSSoapClient
from datetime import date

client = AIMSSoapClient()
client._ensure_connection()

# Pick a flight for today (2026-02-11)
target_date = date(2026, 2, 11)
# We know flight 1218 dep SGN exists from previous steps
flight_no = "1218"
dep = "SGN"

print(f"=== Fetching RAW Leg Members for Flight {flight_no} {dep} on {target_date} ===")

try:
    dt = client._format_date(target_date)
    response = client.client.service.FetchLegMembers(
        UN=client.username_flights,
        PSW=client.password_flights,
        DD=dt["DD"], MM=dt["MM"], YY=dt["YY"],
        Flight=flight_no,
        DEP=dep
    )
    
    if response:
        # Recursive dump of attributes
        def dump_obj(obj, indent=0):
            if obj is None: return
            space = " " * indent
            print(f"{space}Type: {type(obj)}")
            for attr in [a for a in dir(obj) if not a.startswith('_')]:
                try:
                    val = getattr(obj, attr)
                    if not callable(val):
                        if hasattr(val, '__dict__') or 'zeep.objects' in str(type(val)):
                            print(f"{space}{attr}:")
                            dump_obj(val, indent + 4)
                        elif isinstance(val, list):
                            print(f"{space}{attr} (list, len={len(val)}):")
                            for i, item in enumerate(val):
                                print(f"{space}  [{i}]:")
                                dump_obj(item, indent + 6)
                        else:
                            print(f"{space}{attr} = {val}")
                except Exception: pass

        dump_obj(response)
    else:
        print("Empty response.")
except Exception as e:
    print(f"Error: {e}")
