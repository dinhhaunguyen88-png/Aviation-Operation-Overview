"""
Deep comparison: What distinguishes phantom flights from legitimate flights?
Both have flight_date=2026-02-10 and local STD on Feb 11 >= 04:00.
Let me check if the 50 "legitimate" flights (in CSV, local STD on Feb 11)
exist on Feb 9 in DB, while the 15 phantoms don't.
"""
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

# 50 legitimate flights (in CSV as Feb 10, but local STD on Feb 11)
# Sample 10 to check
legit = [
    ('185', 'HAN'), ('302', 'SGN'), ('122', 'SGN'), ('620', 'SGN'), ('1628', 'SGN'),
    ('443', 'HAN'), ('260', 'SGN'), ('421', 'HAN'), ('491', 'HAN'), ('1279', 'HPH'),
    ('813', 'SGN'), ('124', 'SGN'), ('773', 'HAN'), ('179', 'HAN'), ('461', 'HAN'),
]

# 12 phantom flights (NOT in CSV, local STD on Feb 11)
phantoms = [
    ('1120', 'SGN'), ('1121', 'HAN'), ('1123', 'HAN'), ('120', 'SGN'),
    ('1330', 'PQC'), ('1371', 'VCL'), ('1603', 'CXR'), ('167', 'HAN'),
    ('247', 'THD'), ('509', 'HAN'), ('623', 'DAD'), ('833', 'FUK'),
]

print("LEGITIMATE flights (in CSV): Do they exist on Feb 9 too?")
print(f"{'FLT':>8} {'DEP':>4}  {'Feb09':>6} {'Feb10':>6} {'Feb11':>6}  STD_10")
print("-" * 70)
for fn, dep in legit:
    r9 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-09").execute()
    r10 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    r11 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-11").execute()
    has9 = "YES" if r9.data else "NO"
    has10 = "YES" if r10.data else "NO"
    has11 = "YES" if r11.data else "NO"
    std10 = r10.data[0]['std'] if r10.data else '-'
    print(f"{fn:>8} {dep:>4}  {has9:>6} {has10:>6} {has11:>6}  {str(std10):>10}")

print()
print("PHANTOM flights (NOT in CSV): Same check")
print(f"{'FLT':>8} {'DEP':>4}  {'Feb09':>6} {'Feb10':>6} {'Feb11':>6}  STD_10")
print("-" * 70)
for fn, dep in phantoms:
    r9 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-09").execute()
    r10 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    r11 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-11").execute()
    has9 = "YES" if r9.data else "NO"
    has10 = "YES" if r10.data else "NO"
    has11 = "YES" if r11.data else "NO"
    std10 = r10.data[0]['std'] if r10.data else '-'
    print(f"{fn:>8} {dep:>4}  {has9:>6} {has10:>6} {has11:>6}  {str(std10):>10}")

print()
print("KEY INSIGHT:")
print("If legitimate flights exist on Feb 9+10 (duplicate), and phantoms exist ONLY on Feb 10,")
print("then the legitimate ones are truly Feb 10 flights in AIMS (with Feb 9 UTC copies),")
print("while phantoms are Feb 11 flights that got captured in the Feb 10 UTC window.")
print("The difference: legitimate flights' Feb 9 copies prove AIMS considers them a recurring daily flight,")
print("while phantom flights have no Feb 9 copy = they are late evening flights specific to Feb 10 UTC.")
