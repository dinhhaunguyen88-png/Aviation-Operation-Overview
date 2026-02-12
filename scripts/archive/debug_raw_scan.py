import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from aims_soap_client import AIMSSoapClient
from datetime import date

client = AIMSSoapClient()
client._ensure_connection()

target_date = date(2026, 2, 11)
dt = client._format_date(target_date)

print(f"=== Scanning RAW FetchLegMembersPerDay for {target_date} ===")

try:
    response = client.client.service.FetchLegMembersPerDay(
        UN=client.username,
        PSW=client.password,
        DD=dt["DD"], MM=dt["MM"], YY=dt["YY"]
    )
    
    if response and hasattr(response, 'DayMember') and response.DayMember:
        legs = response.DayMember.TAIMSGetLegMembers
        print(f"Found {len(legs)} flight legs.")
        
        all_pos = set()
        all_trnduty = set()
        all_attrs = {}
        
        sick_codes = ["SL", "SCL", "NS", "CSL", "SICK"]
        found_sick = []
        
        for leg in legs:
            if hasattr(leg, 'FMember') and leg.FMember and hasattr(leg.FMember, 'TAIMSMember'):
                members = leg.FMember.TAIMSMember
                if not isinstance(members, list): members = [members]
                
                for m in members:
                    # Collect all position values
                    pos = getattr(m, 'pos', '')
                    if pos: all_pos.add(str(pos).strip())
                    
                    # Collect all trnduty values
                    td = getattr(m, 'trnduty', '')
                    if td: all_trnduty.add(str(td).strip())
                    
                    # Check ALL attributes for sick codes
                    for attr in [a for a in dir(m) if not a.startswith('_')]:
                        val = getattr(m, attr, '')
                        if str(val).upper().strip() in sick_codes:
                            found_sick.append({
                                "crew_id": getattr(m, 'id', ''),
                                "name": getattr(m, 'name', ''),
                                "field": attr,
                                "value": val,
                                "pos": pos,
                                "flight": getattr(leg, 'FlightNo', '')
                            })
        
        print(f"\nUnique positions: {sorted(list(all_pos))}")
        print(f"Unique trnduty: {sorted(list(all_trnduty))}")
        
        if found_sick:
            print(f"\nFOUND {len(found_sick)} SICK-RELATED RECORDS IN RAW SOAP:")
            for s in found_sick[:20]:
                print(f"  Crew: {s['crew_id']} | Field: {s['field']} | Value: {s['value']} | Pos: {s['pos']} | Flight: {s['flight']}")
        else:
            print("\nNo sick-related indicators found in ANY RAW SOAP attribute for ANY member.")
            
    else:
        print("No DayMember data in response.")
except Exception as e:
    print(f"Error: {e}")
