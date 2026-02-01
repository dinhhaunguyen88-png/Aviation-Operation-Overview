from aims_soap_client import AIMSSoapClient
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
client = AIMSSoapClient()

if client.connect():
    dt = date.today()
    print(f"Testing FetchLegMembersPerDay for {dt}...")
    try:
        # Guessing params: UN, PSW, DD, MM, YY
        # Or maybe FromDD...? Let's try matching standard pattern
        # Introspection showed names. We can inspect arguments too if needed (using Zeep)
        # But let's guess standard Header
        
        # We need to construct arguments. 
        # Since I cannot see signature easily, I'll try standard args used in other methods.
        
        # Actually, let's print signature using zeep
        client.client.wsdl.dump()
    except Exception as e:
        print(e)
