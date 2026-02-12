from data_processor import DataProcessor
from datetime import date, timedelta
import json

dp = DataProcessor()

def scan_dates():
    start_date = date(2026, 1, 31)
    print("--- Date Matching Scan ---")
    print(f"{'Date':<12} | {'Flt':<4} | {'Crew':<4} | {'Block':<6} | {'Comp':<4} | {'A/C':<4} | {'OTP':<5}")
    print("-" * 60)
    
    for i in range(15):
        d = start_date + timedelta(days=i)
        try:
            summary = dp.get_dashboard_summary(d)
            print(f"{d.isoformat():<12} | "
                  f"{summary.get('total_flights', 0):<4} | "
                  f"{summary.get('total_crew', 0):<4} | "
                  f"{summary.get('total_block_hours', 0):<6.1f} | "
                  f"{summary.get('total_completed_flights', 0):<4} | "
                  f"{summary.get('total_aircraft_operation', 0):<4} | "
                  f"{summary.get('otp_percentage', 0):<5.1f}%")
        except Exception as e:
            print(f"{d.isoformat()}: Error {e}")

if __name__ == "__main__":
    scan_dates()
