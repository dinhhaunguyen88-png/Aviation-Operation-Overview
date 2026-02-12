from data_processor import DataProcessor
from datetime import date, timedelta

dp = DataProcessor()

def check_recent_dates():
    start_date = date(2026, 1, 29)
    print("--- Flight Counts (Explicit Search) ---")
    for i in range(15):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        count = dp.supabase.table('flights').select('count', count='exact').eq('flight_date', d_str).execute().count
        print(f"{d_str}: {count}")

if __name__ == "__main__":
    check_recent_dates()
