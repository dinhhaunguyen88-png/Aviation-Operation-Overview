from data_processor import DataProcessor

dp = DataProcessor()

try:
    # This is a shot in the dark, but some Supabase setups have this
    res = dp.supabase.rpc('get_service_status').execute()
    print("get_service_status exists")
except:
    pass

try:
    # Information schema for RPCs (functions)
    # Most Supabase users don't expose this, but worth a try
    res = dp.supabase.table('pg_proc').select('*').execute()
    print("pg_proc accessible")
except:
    pass
