"""
Check: Do the 15 phantom flights also exist on Feb 11 in DB?
If yes, they are actually Feb 11 flights that got duplicated to Feb 10 
by our get_day_flights() UTC query.
"""
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

phantoms = [
    ('1120', 'SGN'), ('1121', 'HAN'), ('1123', 'HAN'), ('120', 'SGN'),
    ('1330', 'PQC'), ('1371', 'VCL'), ('1603', 'CXR'), ('167', 'HAN'),
    ('247', 'THD'), ('509', 'HAN'), ('623', 'DAD'), ('833', 'FUK'),
    # Cross-day from Feb 9
    ('176', 'SGN'), ('871', 'TAE'), ('989', 'PUS'),
]

print("Phantom flights check - do they exist on Feb 10 AND Feb 11 in DB?")
print(f"{'FLT':>8} {'DEP':>4}  {'Feb10':>6} {'Feb11':>6}  {'STD_UTC_10':>12} {'STD_UTC_11':>12}")
print("-" * 70)

for fn, dep in phantoms:
    r10 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    r11 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-11").execute()
    
    has10 = "YES" if r10.data else "NO"
    has11 = "YES" if r11.data else "NO"
    std10 = r10.data[0]['std'] if r10.data else '-'
    std11 = r11.data[0]['std'] if r11.data else '-'
    
    print(f"{fn:>8} {dep:>4}  {has10:>6} {has11:>6}  {str(std10):>12} {str(std11):>12}")

print()
print("If phantom flights exist on BOTH dates with SAME STD,")
print("they are duplicates. The Feb 10 copies are UTC-window artifacts")
print("and should be removed (the real date is Feb 11 per AIMS/DayRepReport).")
