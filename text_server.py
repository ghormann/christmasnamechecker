#
# This is the main program for the server and receives 
# text messages from twilio and sends them to  the
# home network

from flask import Flask, request, redirect, send_from_directory
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
masterData={};
masterData["queue"]=[];
masterData["history"]=[];

app = Flask(__name__, static_url_path='')

def addHistory(phone, name, isValid):
    rec = {}
    rec["phone"] = phone
    rec["name"] = name
    rec["valid"] = isValid
    masterData["history"].insert(0,rec)
    while (len(masterData["history"]) > 50):
       masterData["history"].pop()

def notifyAdmin(message):
    message = client.messages.create(
        to=config["notifyAdmin"],
        from_=config["fromPhone"],
        body=message)

@app.route("/queueData", methods=['GET', 'POST'])
def queuedata_reply():
    return json.dumps(masterData)

@app.route("/status", methods=['GET', 'POST'])
def status_reply():
    return str("Running")

@app.route("/static/<path:path>", methods=['GET'])
def send_static(path):
    return send_from_directory('static', path)

@app.route("/update", methods=['GET', 'POST'])
def update_reply():
    validator.addNames("data/custom.txt")
    log_file.write("Reloading names")
    return str("loaded custom")

@app.route("/addName", methods=['GET'])
def add_admin_name_reply():
    name = request.args.get('name')
    pos = request.args.get('pos')
    log_file.write('Adding name from admin: ' + name)
    mqtt.publishName(name)
    addHistory('Admin', name, True);
    return str("Done")


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

    addHistory(fromNum, textIn, isValid);
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message(msg)

    return str(resp)

if __name__ == "__main__":
    addHistory('123-456-7890', 'Test', False);
    addHistory('123-456-7890', 'Test2', False);
    app.run(host='127.0.0.1', port=9999)
