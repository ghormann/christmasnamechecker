#
# This is the main program for the server and receives 
# text messages from twilio and sends them to  the
# home network

from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import json
import sys

config = json.load(open('greglights_config.json'))
client = Client(config["account_sid"], config["auth_token"]) 

def notifyAdmin(message):
    message = client.messages.create(
        to="+15139738669",
        from_=config["fromPhone"],
        body=message)

if __name__ == "__main__":
    notifyAdmin("Keithie was reviewed and added.")
