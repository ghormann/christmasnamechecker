#
# This is the main program for the server and receives 
# text messages from twilio and sends them to  the
# home network

from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from name_validator import NameValidator
from mqtt import MQTTClient

mqtt = MQTTClient()
validator = NameValidator("data/all_names.txt")
log_file = open("logs/text.log", "a")

app = Flask(__name__)

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
   
    msg=str(isValid) + "|" + fromCity + "|" + fromState + "|" + fromCountry
    msg += "|" + fromZip + "|" + fromNum + "|" + textIn 
    
    log_file.write(msg)
    log_file.write("\n")
    log_file.flush()

    msg = "The provided name \"" + textIn + "\" wasn't found in our database of 96,000"
    msg += " names.   I'm afraid it won't be displayed tonight.  I've flagged it to be "
    msg += " reviewed. If approved, it will be added to the database in the next few days."

    if isValid:
        mqtt.publishName(textIn)
        msg = "Thanks! Your name should display soon." 

    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message(msg)

    return str(resp)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=9999)