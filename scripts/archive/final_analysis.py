"""
Final analysis: Compare the 5 remaining phantom flights vs the 50 legitimate flights.
Both have prev-date copies and target-date copies. What distinguishes them?

Check if the STD on the prev-date copy matches the target-date copy.
For legitimate daily flights, the STD should be the same (same flight, same time, daily).
For phantoms, the prev-date copy might have a DIFFERENT STD or be a different flight entirely.
"""
from dotenv import load_dotenv
import os
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

print("=== 5 REMAINING PHANTOM FLIGHTS (NOT in CSV for Feb 10) ===")
print(f"{'FLT':>8} {'DEP':>4}  {'STD_Feb09':>12} {'STD_Feb10':>12} {'MATCH':>6}")
print("-" * 60)
phantoms_5 = [('1330', 'PQC'), ('176', 'SGN'), ('833', 'FUK'), ('871', 'TAE'), ('989', 'PUS')]
for fn, dep in phantoms_5:
    r9 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-09").execute()
    r10 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    std9 = r9.data[0]['std'] if r9.data else '-'
    std10 = r10.data[0]['std'] if r10.data else '-'
    match = "YES" if std9 == std10 else "NO"
    print(f"{fn:>8} {dep:>4}  {str(std9):>12} {str(std10):>12} {match:>6}")

print()
print("=== SAMPLE LEGITIMATE FLIGHTS (IN CSV for Feb 10) ===")
print(f"{'FLT':>8} {'DEP':>4}  {'STD_Feb09':>12} {'STD_Feb10':>12} {'MATCH':>6}")
print("-" * 60)
legit = [('185', 'HAN'), ('302', 'SGN'), ('122', 'SGN'), ('620', 'SGN'), ('1628', 'SGN'),
         ('443', 'HAN'), ('260', 'SGN'), ('421', 'HAN'), ('491', 'HAN'), ('1279', 'HPH')]
for fn, dep in legit:
    r9 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-09").execute()
    r10 = sb.table("flights").select("std").eq("flight_number", fn).eq("departure", dep).eq("flight_date", "2026-02-10").execute()
    std9 = r9.data[0]['std'] if r9.data else '-'
    std10 = r10.data[0]['std'] if r10.data else '-'
    match = "YES" if std9 == std10 else "NO"
    print(f"{fn:>8} {dep:>4}  {str(std9):>12} {str(std10):>12} {match:>6}")
