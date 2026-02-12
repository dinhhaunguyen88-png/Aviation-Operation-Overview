from data_processor import DataProcessor

dp = DataProcessor()

# Query information_schema for unique constraints on 'flights' table
sql = """
SELECT
    tc.constraint_name, 
    kcu.column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'UNIQUE' AND tc.table_name = 'flights';
"""

# We can't run raw SQL directly via Supabase client easily if not exposed via RPC
# But we can try to guess or use the error message from a test upsert

def test_upsert_constraint():
    test_data = [
        {"flight_date": "2026-02-10", "flight_number": "TEST999", "departure": "ABC"},
        {"flight_date": "2026-02-10", "flight_number": "TEST999", "departure": "DEF"}
    ]
    try:
        print("Testing upsert with (flight_date, flight_number, departure) on aims_flights...")
        res = dp.supabase.table('aims_flights').upsert(test_data, on_conflict="flight_date,flight_number,departure").execute()
        print("SUCCESS: Constraint (flight_date, flight_number, departure) works on aims_flights.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_upsert_constraint()
