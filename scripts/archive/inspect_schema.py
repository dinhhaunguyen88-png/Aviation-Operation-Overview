import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check_schema():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    tables = ["flights", "crew_members", "crew_flight_hours", "standby_records"]
    
    print("Checking Table Schemas:")
    for table in tables:
        print(f"\n--- Table: {table} ---")
        try:
            # Try to get one row to see columns
            result = supabase.table(table).select("*").limit(1).execute()
            if result.data:
                print("Columns found (from sample row):")
                for col in result.data[0].keys():
                    print(f" - {col}")
            else:
                print("No data in table to inspect columns.")
        except Exception as e:
            print(f"Error inspecting {table}: {e}")

if __name__ == "__main__":
    check_schema()
