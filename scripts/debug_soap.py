import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aims_soap_client import AIMSSoapClient
from datetime import date
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_soap")

def debug():
    client = AIMSSoapClient()
    print("Connecting...")
    if not client.connect():
        print("Connection failed")
        return

    # 1. Print available operations
    print("\n=== Available SOAP Operations ===")
    for service_name, service in client.client.wsdl.services.items():
        print(f"Service: {service_name}")
        for port_name, port in service.ports.items():
            print(f"  Port: {port_name}")
            for op_name, op in port.binding._operations.items():
                print(f"    - {op_name}")

    # 2. Inspect GetCrewList response
    print("\n=== Testing GetCrewList Response Structure ===")
    today = date.today()
    try:
        # Using raw client to get raw response object
        # Replicating get_crew_list call logic
        from_dt = client._format_date(today)
        to_dt = client._format_date(today)
        
        print(f"Calling GetCrewList for {today}...")
        response = client.client.service.GetCrewList(
            UN=client.username,
            PSW=client.password,
            ID=0,
            PrimaryQualify=True,
            FmDD=from_dt["DD"],
            FmMM=from_dt["MM"],
            FmYY=from_dt["YY"],
            ToDD=to_dt["DD"],
            ToMM=to_dt["MM"],
            ToYY=to_dt["YY"],
            BaseStr="",
            ACStr="",
            PosStr=""
        )
        
        print(f"\nResponse Type: {type(response)}")
        print(f"Response Dir: {dir(response)}")
        
        if hasattr(response, 'GetCrewListCount'):
            print(f"Count: {response.GetCrewListCount}")
            
        if hasattr(response, 'CrewList'):
            print(f"CrewList exists. Type: {type(response.CrewList)}")
            print(f"CrewList Dir: {dir(response.CrewList)}")
            
            # Replicate the logic from aims_soap_client
            crew_items_list = response.CrewList
            if hasattr(crew_items_list, 'TAIMSGetCrewItm'):
                crew_items_list = crew_items_list.TAIMSGetCrewItm
            
            try:
                if not isinstance(crew_items_list, list):
                     crew_items_list = [crew_items_list]

                print(f"Length of crew_items_list: {len(crew_items_list)}")
                if len(crew_items_list) > 0:
                    first = crew_items_list[0]
                    print(f"First item type: {type(first)}")
                    print(f"First item dir: {dir(first)}")
                    # Try accessing common fields
                    print(f"Prop 'CrewID': {getattr(first, 'CrewID', 'N/A')}")
                    print(f"Prop 'ID': {getattr(first, 'ID', 'N/A')}")
            except Exception as e:
                print(f"CrewList iteration/len failed: {e}")
                
            # Check if there is a nested list
            # Zeep sometimes puts the list in 'TAIMSGetCrewItm' or similar key inside
            for key in dir(response.CrewList):
                if not key.startswith('_'):
                     val = getattr(response.CrewList, key)
                     print(f"Field {key}: {type(val)}")
        else:
            print("CrewList attribute MISSING")
            
    except Exception as e:
        print(f"GetCrewList failed: {e}")

    # 3. Test Roster for First Crew
    print("\n=== Testing CrewMemberRosterDetailsForPeriod Structure ===")
    first_crew_id = None
    # Try to extract ID from local variables if they exist
    try:
        if 'crew_items_list' in locals() and len(crew_items_list) > 0:
            first = crew_items_list[0]
            first_crew_id = getattr(first, 'Id', None)
    except:
        pass
        
    if first_crew_id:
        print(f"Using Crew ID: {first_crew_id}")
        try:
             # Construct date params
             from datetime import timedelta
             start_date = today - timedelta(days=5)
             end_date = today + timedelta(days=5)
             
             dt_start = client._format_date(start_date)
             dt_end = client._format_date(end_date)

             print(f"Calling Roster for {start_date} to {end_date}...")
             
             roster_response = client.client.service.CrewMemberRosterDetailsForPeriod(
                UN=client.username,
                PSW=client.password,
                CrewID=first_crew_id,
                FromDD=dt_start["DD"],
                FromMMonth=dt_start["MM"],
                FromYYYY=dt_start["YY"],
                ToDD=dt_end["DD"],
                ToMMonth=dt_end["MM"],
                ToYYYY=dt_end["YY"]
             )
             
             print(f"Roster Response Type: {type(roster_response)}")
             print(f"Roster Response Dir: {dir(roster_response)}")
             
             # Drill down
             for key in dir(roster_response):
                 if not key.startswith('_'):
                     val = getattr(roster_response, key)
                     print(f"Field '{key}': {type(val)}")
                     
                     if "ArrayOf" in str(type(val)) or isinstance(val, list):
                         inner = val
                         # Unwrap likely Zeep list wrapper
                         possible_inner_keys = [k for k in dir(inner) if not k.startswith('_') and not callable(getattr(inner, k))]
                         if possible_inner_keys:
                             print(f"  -> Inner keys: {possible_inner_keys}")
                             first_inner_key = possible_inner_keys[0]
                             inner_list = getattr(inner, first_inner_key)
                             print(f"  -> Inner list type: {type(inner_list)}")
                             if isinstance(inner_list, list) and len(inner_list) > 0:
                                 print(f"  -> First item: {inner_list[0]}")
                                 print(f"  -> First item dir: {dir(inner_list[0])}")

        except Exception as e:
            print(f"Roster call failed: {e}")
    else:
        print("No Crew ID found to test Roster.")

if __name__ == "__main__":
    debug()
