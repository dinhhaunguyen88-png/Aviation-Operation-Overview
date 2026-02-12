"""Check SGN crew overlap with FTL data."""
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get 200 SGN crew IDs
sgn = sb.table('crew_members').select('crew_id').ilike('base', 'SGN%').limit(200).execute()
sgn_ids = [x['crew_id'] for x in sgn.data]
print(f"SGN crew sample: {len(sgn_ids)} IDs")

# Check which ones have FTL data
ftl = sb.table('crew_flight_hours').select('crew_id, hours_28_day').in_('crew_id', sgn_ids[:100]).gt('hours_28_day', 0).execute()
print(f"Of first 100 SGN crew, {len(ftl.data)} have FTL hours > 0")
for x in ftl.data[:5]:
    print(f"  crew_id={x['crew_id']} hours={x['hours_28_day']}")

# Check how many total FTL records have hours > 0
ftl_total = sb.table('crew_flight_hours').select('crew_id', count='exact').gt('hours_28_day', 0).execute()
print(f"\nTotal FTL records with hours > 0: {ftl_total.count}")

# Check base distribution of FTL crew
ftl_sample = sb.table('crew_flight_hours').select('crew_id').gt('hours_28_day', 50).limit(50).execute()
ftl_cids = [x['crew_id'] for x in ftl_sample.data]
if ftl_cids:
    cm = sb.table('crew_members').select('crew_id, base').in_('crew_id', ftl_cids).execute()
    bases = {}
    for c in cm.data:
        b = (c.get('base', '') or '').strip() or 'EMPTY'
        bases[b] = bases.get(b, 0) + 1
    print(f"\nBase distribution of crew with 50+ hours (sample 50): {bases}")
