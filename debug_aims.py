import os
import logging
from datetime import date, timedelta
from aims_soap_client import AIMSSoapClient
from dotenv import load_dotenv

# Configure logging to see everything
logging.basicConfig(level=logging.INFO)
load_dotenv()

def debug_aims():
    print("="*60)
    print("AIMS Connection Debugger")
    print("="*60)
    
    client = AIMSSoapClient()
    
    print(f"[*] WSDL URL: {client.wsdl_url}")
    print(f"[*] Username: {client.username}")
    
    print("\n[1] Testing Connection...")
    try:
        connected = client.connect()
        if connected:
            print("[OK] Connection established (WSDL parsed)")
        else:
            print("[FAIL] Connection failed")
            return
    except Exception as e:
        print(f"[ERROR] Connection Exception: {e}")
        return

    print("\n[2] Testing GetCrewList...")
    try:
        today = date.today()
        response = client.client.service.GetCrewList(
            UN=client.username,
            PSW=client.password,
            ID=0,
            PrimaryQualify=True,
            FmDD=today.strftime("%d"),
            FmMM=today.strftime("%m"),
            FmYY=today.strftime("%Y"),
            ToDD=today.strftime("%d"),
            ToMM=today.strftime("%m"),
            ToYY=today.strftime("%Y"),
            BaseStr="",
            ACStr="",
            PosStr=""
        )
        print(f"[OK] GetCrewList successful!")
        if hasattr(response, 'CrewList') and response.CrewList:
            print(f"Records found: {len(response.CrewList)}")
            # Show first crew member
            c = response.CrewList[0]
            print(f"Sample Crew: {getattr(c, 'CrewName', 'N/A')} (ID: {getattr(c, 'CrewID', 'N/A')})")
        else:
            print("No records returned.")
    except Exception as e:
        print(f"[ERROR] GetCrewList failed: {e}")

    print("\n[3] Testing CrewMemberRosterDetailsForPeriod...")
    try:
        today = date.today()
        # Using ID=0 or first crew ID if found
        crew_id = 1 # Default test
        if hasattr(response, 'CrewList') and response.CrewList:
            crew_id = getattr(response.CrewList[0], 'CrewID', 1)

        response = client.client.service.CrewMemberRosterDetailsForPeriod(
            UN=client.username,
            PSW=client.password,
            ID=crew_id, 
            FmDD=today.strftime("%d"),
            FmMM=today.strftime("%m"),
            FmYY=today.strftime("%Y"),
            ToDD=(today + timedelta(days=7)).strftime("%d"),
            ToMM=(today + timedelta(days=7)).strftime("%m"),
            ToYY=(today + timedelta(days=7)).strftime("%Y")
        )
        print(f"[OK] CrewMemberRosterDetailsForPeriod successful!")
        if hasattr(response, 'CrewRostList') and response.CrewRostList:
            print(f"Items found: {len(response.CrewRostList)}")
        else:
            print("No roster items found.")
    except Exception as e:
        print(f"[ERROR] CrewMemberRosterDetailsForPeriod failed: {e}")

if __name__ == "__main__":
    debug_aims()
