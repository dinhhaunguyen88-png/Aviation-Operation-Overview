from aims_soap_client import AIMSSoapClient
import logging

logging.basicConfig(level=logging.ERROR)
client = AIMSSoapClient()

if client.connect():
    print("Available Service Methods:")
    for method in dir(client.client.service):
        if not method.startswith("_"):
            print(f"- {method}")
