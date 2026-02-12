"""
Check: Are the 49 CSV flights dated 11/02/26 present in the system?
These are flights that AIMS assigns to Feb 11 UTC but depart before 04:00 local,
so they belong to Feb 10 ops day.
"""
import csv, re, json, urllib.request

# Parse CSV 11/02 flights
csv_11feb = []
with open('DayRepReport10Feb.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 6:
            continue
        date_str = row[0].strip()
        if date_str != '11/02/26':
            continue
        flt = row[1].strip().replace(' *', '').strip()
        flt_base = re.sub(r'[A-Z]+$', '', flt)
        dep = row[4].strip()
        arr = row[5].strip()
        std = row[6].strip() if len(row) > 6 else ''
        csv_11feb.append({'flt': flt, 'flt_base': flt_base, 'dep': dep, 'arr': arr, 'std_local': std})

# Fetch system flights
r = urllib.request.urlopen('http://localhost:5000/api/flights?date=2026-02-10')
data = json.loads(r.read().decode())
sys_flights = data.get('data', {}).get('flights', [])

# Build system lookup
sys_lookup = set()
for sf in sys_flights:
    fn = sf.get('flight_number', '').strip()
    dep = sf.get('departure', '').strip()
    fn_base = re.sub(r'[A-Z]+$', '', fn)
    sys_lookup.add((fn, dep))
    sys_lookup.add((fn_base, dep))

print(f"CSV 11/02 flights: {len(csv_11feb)}")
print()

found = 0
missing = 0

for cf in csv_11feb:
    in_sys = (cf['flt'], cf['dep']) in sys_lookup or (cf['flt_base'], cf['dep']) in sys_lookup
    status = "OK" if in_sys else "MISSING"
    if in_sys:
        found += 1
    else:
        missing += 1
    if not in_sys:
        print(f"  MISSING: {cf['flt']:>8} {cf['dep']}->{cf['arr']} STD_LOCAL={cf['std_local']}")

print(f"\nFound in system: {found}")
print(f"Missing from system: {missing}")
