from api_server import _sync_today_flights
from datetime import date
import logging

# Enable logging to see sync progress
logging.basicConfig(level=logging.INFO)

def trigger_sync():
    target_date = date(2026, 2, 10)
    print(f"--- Triggering CLEAN sync for {target_date} ---")
    _sync_today_flights(target_date)
    print("Sync complete.")

if __name__ == "__main__":
    trigger_sync()
