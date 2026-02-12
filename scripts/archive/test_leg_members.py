from aims_soap_client import AIMSSoapClient
from datetime import date
import logging
import datetime

logging.basicConfig(level=logging.INFO)
client = AIMSSoapClient()

if client.connect():
    dt = date.today() # 2026-02-01
    
    # Credentials
    UN = client.username
    PSW = client.password
    
    # FetchLegMembers Test
    # Guessing args: Airline?, FlightNo, Date...
    # Likely: UN, PSW, CarrierCode, FlightNo, DD, MM, YY
    print("Trying FetchLegMembers...")
    try:
         # Need a valid flight number. From logs I saw '883'
         f_no = "883"
         dep = "SGN"
         
         res = client.client.service.FetchLegMembers(
            UN=client.username_flights, 
            PSW=client.password_flights,
            DD=str(dt.day).zfill(2),
            MM=str(dt.month).zfill(2),
            YY=str(dt.year),
            Flight=f_no,
            DEP=dep
        )
         print("Success FetchLegMembers!")
         print(res)
    except Exception as e:
         print(f"Failed FetchLegMembers: {e}")
         
    # Try with Main Creds and Correct Args
    print("Trying FetchLegMembers (Main Creds, Correct Args)...")
    try:
         # Need a valid flight. Log said 883?
         # And DEP airport. VJ883 is SGN-KIX? Dep SGN?
         # I'll guess SGN. If wrong, API might say "Flight not found".
         f_no = "883"
         dep = "SGN" 
         
         res = client.client.service.FetchLegMembers(
            UN=client.username, 
            PSW=client.password,
            DD=str(dt.day).zfill(2),
            MM=str(dt.month).zfill(2),
            YY=str(dt.year),
            Flight=f_no,
            DEP=dep
        )
         print("Success FetchLegMembers (Main)!")
         print(res)
    except Exception as e:
         print(f"Failed FetchLegMembers (Main): {e}")
