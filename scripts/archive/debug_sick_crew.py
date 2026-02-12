"""Debug: Dump full TAIMSMember attributes to find SL/SCL/NS indicator."""
import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

from aims_soap_client import AIMSSoapClient
from datetime import date

client = AIMSSoapClient()
client._ensure_connection()

target = date(2026, 2, 11)
dt = client._format_date(target)

response = client.client.service.FetchLegMembersPerDay(
    UN=client.username, PSW=client.password,
    DD=dt["DD"], MM=dt["MM"], YY=dt["YY"]
)

dm = response.DayMember
legs = dm.TAIMSGetLegMembers

print(f"Total legs/groups: {len(legs)}")

# Look at first leg
leg = legs[0]
leg_attrs = [a for a in dir(leg) if not a.startswith('_')]
print(f"\nLeg attrs: {leg_attrs}")
for attr in leg_attrs:
    val = getattr(leg, attr)
    if not callable(val) and attr != 'FMember':
        print(f"  {attr} = {val}")

# Get member list
members = leg.FMember
if hasattr(members, 'TAIMSMember'):
    members = members.TAIMSMember
    if not isinstance(members, list):
        members = [members]

print(f"\nLeg FCount={leg.FCount}, actual members={len(members)}")

# Dump ALL attrs of first member
m = members[0]
m_attrs = [a for a in dir(m) if not a.startswith('_')]
print(f"\nTAIMSMember attrs ({len(m_attrs)}): {m_attrs}")
for attr in m_attrs:
    val = getattr(m, attr)
    if not callable(val):
        print(f"  {attr} = {val}")

# Now search ALL members across ALL legs for SL/SCL/NS
print(f"\n=== Searching ALL {response.Count} members for SL/SCL/NS ===")
sick_codes = {"SL", "SCL", "NS"}
sick_crew = []
all_indicators = set()

for leg in legs:
    fmembers = leg.FMember
    if hasattr(fmembers, 'TAIMSMember'):
        fmembers = fmembers.TAIMSMember
        if not isinstance(fmembers, list):
            fmembers = [fmembers]
    elif not isinstance(fmembers, list):
        fmembers = [fmembers] if fmembers else []
    
    for m in fmembers:
        # Check ALL string attributes
        for attr in [a for a in dir(m) if not a.startswith('_')]:
            val = getattr(m, attr, None)
            if isinstance(val, str):
                stripped = val.upper().strip()
                if attr == 'Indicator' or attr == 'indicator':
                    all_indicators.add(stripped)
                if stripped in sick_codes:
                    crew_id = getattr(m, 'CrewCode', '') or getattr(m, 'CrewID', '') or getattr(m, 'ID', '')
                    crew_name = getattr(m, 'Name', '') or getattr(m, 'CrewName', '')
                    pos = getattr(m, 'Position', '') or getattr(m, 'Pos', '') or getattr(m, 'FunctionCode', '')
                    sick_crew.append({
                        "crew_id": crew_id, "name": crew_name, "position": pos,
                        "field": attr, "value": stripped
                    })

if sick_crew:
    print(f"\n>>> FOUND {len(sick_crew)} sick crew! <<<")
    for s in sick_crew[:30]:
        print(f"  crew={s['crew_id']}, name={s['name']}, pos={s['position']}, "
              f"{s['field']}='{s['value']}'")
else:
    print("No SL/SCL/NS found in any attribute!")

# Show unique values for key fields    
print(f"\nAll Indicator values: {sorted(all_indicators) if all_indicators else 'N/A'}")

# Check indicator field specifically
print(f"\n=== Specific field scan ===")
all_vals = {}
for leg in legs:
    fmembers = leg.FMember
    if hasattr(fmembers, 'TAIMSMember'):
        fmembers = fmembers.TAIMSMember
        if not isinstance(fmembers, list):
            fmembers = [fmembers]
    elif not isinstance(fmembers, list):
        fmembers = [fmembers] if fmembers else []
    for m in fmembers:
        for attr in [a for a in dir(m) if not a.startswith('_')]:
            val = getattr(m, attr, None)
            if isinstance(val, str) and val.strip():
                if attr not in all_vals:
                    all_vals[attr] = set()
                all_vals[attr].add(val.strip())

for attr, vals in sorted(all_vals.items()):
    if len(vals) <= 25:
        print(f"  {attr}: {sorted(vals)}")
    else:
        print(f"  {attr}: {len(vals)} unique values (sample: {sorted(list(vals))[:10]})")
