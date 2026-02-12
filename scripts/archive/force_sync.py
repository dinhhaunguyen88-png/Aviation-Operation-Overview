from api_server import app, sync_aims_data
from data_processor import DataProcessor
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def force_sync():
    """Manually force AIMS data sync."""
    print("="*60)
    print("Forcing AIMS Data Sync")
    print("="*60)
    
    with app.app_context():
        try:
            print("[*] Starting sync job...")
            sync_aims_data()
            print("[SUCCESS] Sync job completed.")
            
            # Verify data
            processor = DataProcessor()
            crew_hours = processor.get_crew_hours()
            print(f"\n[VERIFY] Found {len(crew_hours)} crew flight hour records for today.")
            
        except Exception as e:
            print(f"[ERROR] Sync failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    force_sync()
