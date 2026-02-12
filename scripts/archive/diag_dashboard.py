"""Check: Are the 9 phantom Feb 10 flights cancelled or just missing from DayRep?"""
import urllib.request, json

r = urllib.request.urlopen('http://localhost:5000/api/flights?date=2026-02-10')
data = json.loads(r.read().decode())
flights = data.get('data', {}).get('flights', [])

# The 9+3 phantom flights NOT in DayRepReport
phantom_numbers = {
    '1120', '1121', '1123', '120', '1330', '1371', '1603', '167', '247', '509', '623', '833',
    '176', '871', '989'  # Feb 9 crossovers not in DayRep
}

# Also check: some of these might just be from a DIFFERENT ops day
# DayRepReport shows 10/02 ops = 471 flights on 10/02 + 49 on 11/02 = 520 total
# The 11/02 flights are all STD_LOCAL 00:00-03:45

print("Phantom flights NOT in DayRepReport10Feb.csv:")
print(f"{'FLT':>8} {'DB_DATE':>12} {'DEP':>4} {'ARR':>4} {'STD_UTC':>8} {'LOCAL':>6} {'STATUS':>10} {'REG':>10}")
print("-" * 80)

for f in sorted(flights, key=lambda x: x.get('flight_number', '')):
    fn = f.get('flight_number', '')
    if fn in phantom_numbers:
        print(f"{fn:>8} {f.get('_original_db_date',''):>12} {f.get('departure',''):>4} {f.get('arrival',''):>4} {(f.get('std','') or '')[:5]:>8} {(f.get('local_std','') or ''):>6} {f.get('status',''):>10} {f.get('aircraft_reg',''):>10}")

# Now check: What DayRepReport flight numbers are close to these?
# Some could be suffix variants
print()
print("Checking suffixed variants:")
import csv, re
csv_flights = {}
with open('DayRepReport10Feb.csv', 'r') as f2:
    reader = csv.reader(f2)
    for row in reader:
        if len(row) < 6: continue
        date_str = row[0].strip()
        flt = row[1].strip().replace(' *', '')
        if not flt or not re.match(r'\d{2}/\d{2}/\d{2}', date_str): continue
        dep = row[4].strip()
        arr = row[5].strip()
        std = row[6].strip() if len(row) > 6 else ''
        base = flt.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        csv_flights[flt] = {'base': base, 'date': date_str, 'dep': dep, 'arr': arr, 'std': std}

for pn in sorted(phantom_numbers):
    # Find any CSV flight with same base number
    matches = [(k, v) for k, v in csv_flights.items() if v['base'] == pn]
    if matches:
        for k, v in matches:
            print(f"  System {pn:>6} -> CSV has {k:>8} ({v['date']} {v['dep']}->{v['arr']} STD={v['std']})")

# Check: Does DayRepReport include some of these phantom flights on a DIFFERENT date?
# Check if they might be on 09/02 DayRepReport instead
print()
print("Looking at flight numbers that appear in DayRep under a DIFFERENT base:")
for pn in sorted(phantom_numbers):
    if pn in csv_flights:
        v = csv_flights[pn] 
        print(f"  {pn} IS in CSV: {v['date']} {v['dep']}->{v['arr']} STD={v['std']}")
    else:
        print(f"  {pn} NOT in CSV at all")
