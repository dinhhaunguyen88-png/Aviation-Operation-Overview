from data_processor import DataProcessor
from collections import Counter

dp = DataProcessor()

def check_dates():
    res = dp.supabase.table('flights').select('flight_date').execute()
    dates = [r['flight_date'] for r in res.data]
    counts = Counter(dates)
    
    print("--- Flight Counts by Date ---")
    for d in sorted(counts.keys()):
        print(f"{d}: {counts[d]}")

if __name__ == "__main__":
    check_dates()
