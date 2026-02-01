from aims_soap_client import AIMSSoapClient
import logging

logging.basicConfig(level=logging.ERROR)
client = AIMSSoapClient()

if client.connect():
    print("FetchLegMembers Signature:")
    try:
        # accessing the method on the service proxy
        method = client.client.service.FetchLegMembers
        print(method)
    except Exception as e:
        print(f"Error: {e}")
