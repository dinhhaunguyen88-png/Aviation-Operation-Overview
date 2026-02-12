from data_processor import DataProcessor

dp = DataProcessor()

def list_tables():
    # Supabase/PostgREST doesn't have a direct 'list tables' API via the client easily
    # but we can try to query information_schema if permitted, or just check the SQL file.
    # Alternative: check aims_etl_manager.py for table list
    print("--- Checking aims_etl_manager.py for table list ---")

if __name__ == "__main__":
    list_tables()
