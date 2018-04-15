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
        to=config["notifyAdmin"],
        from_=config["fromPhone"],
        body=message)

if __name__ == "__main__":
    #notifyAdmin("This is a test. It is only a test")
    if (len(sys.argv) < 2):
        print("Usage: python text_me.py \"message\"")
    else:
        notifyAdmin(sys.argv[1])
