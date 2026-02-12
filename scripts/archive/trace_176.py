from data_processor import DataProcessor
dp = DataProcessor()
res = dp.supabase.table('flights').select('*').eq('flight_number', '176').execute()
for r in res.data:
    print(f"ID: {r.get('id')}, Date: {r['flight_date']}, Std: {r['std']}, Atd: {r['atd']}, Status: {r['status']}, Source: {r.get('source')}")
