#
# This is the main program for the server and receives 
# text messages from twilio and sends them to  the
# home network

from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from name_validator import NameValidator
from mqtt import MQTTClient
import datetime
from twilio.rest import Client
import json

config = json.load(open('greglights_config.json'))
mqtt = MQTTClient()
client = Client(config["account_sid"], config["auth_token"]) 
validator = NameValidator("data/all_names.txt")
validator.addNames("data/custom.txt")
log_file = open("logs/text.log", "a")

app = Flask(__name__)

def notifyAdmin(message):
    message = client.messages.create(
        to=config["notifyAdmin"],
        from_=config["fromPhone"],
        body=message)

@app.route("/status", methods=['GET', 'POST'])
def status_reply():
    return str("Running")

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""
    textIn = ' '.join(request.values['Body'].splitlines())
    fromCity = request.values['FromCity']
    fromState = request.values['FromState']
    fromCountry = request.values['FromCountry']
    fromZip = request.values['FromZip']
    fromNum = request.values['From']
    isValid = validator.isValid(textIn)
    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
   
    msg= ts + "|" + str(isValid) + "|" + fromCity + "|" + fromState + "|" + fromCountry
    msg += "|" + fromZip + "|" + fromNum + "|" + textIn 
    
    log_file.write(msg)
    log_file.write("\n")
    log_file.flush()

    msg = "\"" + textIn + "\" isn't a pre-approved first name and has submitted for human review."
    msg += " If approved, it will be available in 2-3 days."

    if isValid:
        mqtt.publishName(textIn)
        msg = "Thanks " + textIn +  "! Your name should display soon." 
    else:
        notifyAdmin("Invalid Name on lights: " + textIn)

    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message(msg)

    return str(resp)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=9999)
