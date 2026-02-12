from data_processor import DataProcessor

dp = DataProcessor()

# Try to list tables via a trick or check schema cache
try:
    # PostgREST 10+ has a way to see tables by querying '/' but that's HTTP
    # We can try to query information_schema if allowed
    res = dp.supabase.rpc('get_tables').execute()
    print(res.data)
except:
    print("Could not use RPC. Trying direct SQL if possible or just sampling common names.")
    tables = ['flights', 'aims_flights', 'aims_flight_mod_log', 'FlightScheduleModificationLog']
    for t in tables:
        try:
            res = dp.supabase.table(t).select('count', count='exact').limit(1).execute()
            print(f"Table '{t}' exists and has {res.count} rows.")
        except:
            print(f"Table '{t}' does not exist or access denied.")
