from aims_soap_client import AIMSSoapClient
from datetime import date
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
client = AIMSSoapClient()

def fetch_schedule(cid):
    try:
        # random small sleep to spread load slightly?
        return client.get_crew_schedule(date.today(), date.today(), crew_id=cid)
    except Exception as e:
        return None

if client.connect():
    # Get a list of crew to test
    print("Fetching CP List...")
    crew_list = client.get_crew_list(date.today(), date.today(), position="CP")
    test_ids = [c['crew_id'] for c in crew_list[:20]] # Test 20
    print(f"Testing concurrency with {len(test_ids)} crew...")
    
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_schedule, cid): cid for cid in test_ids}
        for future in as_completed(futures):
            results.append(future.result())
            
    end = time.time()
    print(f"Finished in {end-start:.2f} seconds")
    print(f"Success count: {len([r for r in results if r is not None])}")
