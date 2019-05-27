
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
import time
import math

config = json.load(open('greglights_config.json'))
mqtt = MQTTClient()
client = Client(config["account_sid"], config["auth_token"]) 
validator = NameValidator("data/all_names.txt")
validator.addNames("data/custom.txt")
log_file = open("logs/text.log", "a")
masterData={};
masterData["queue"]=[];
masterData["queueLow"]=[];
masterData["history"]=[];
masterData["outPhone"]=[];

app = Flask(__name__, static_url_path='')

def num_recent_calls(phone):
    cnt =0
    for rec in masterData["history"]:
        if rec["phone"] == phone and rec["valid"] :
            diff = time.time() - rec["ts"]
            if (diff < 600): # 10 min
               cnt += 1

    return cnt

def addHistory(phone, name, isValid):
    rec = {}
    rec["phone"] = phone
    rec["name"] = name
    rec["valid"] = isValid
    rec["ts"] = time.time()
    masterData["history"].insert(0,rec)
    while (len(masterData["history"]) > 200):
       masterData["history"].pop()

def addOutHistory(phone, message):
    rec = {}
    rec["phone"] = phone
    rec["message"] = message
    rec["ts"] = time.time()
    masterData["outPhone"].insert(0,rec)
    while (len(masterData["outPhone"]) > 20):
       masterData["outPhone"].pop()
   

def notifyPhone(number, message):
    message = client.messages.create(
        to=number,
        from_=config["fromPhone"],
        body=message)

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

@app.route("/adminReply", methods=['GET'])
def send_text_reply():
    to = request.args.get('to')
    message = request.args.get('message')
    log_file.write('To ' + to + ": " + message)
    notifyPhone(to, message)
    addOutHistory(to, message)
    return str("sent")

@app.route("/addName", methods=['GET'])
def add_admin_name_reply():
    name = request.args.get('name')
    pos = request.args.get('pos')
    if "first" == pos: 
        mqtt.publishNameFirst(name)
        log_file.write('Adding name from admin: to Front: ' + name + '\n')
    elif "remove" == pos: 
        mqtt.removeName(name)
        log_file.write('Removing name from admin: to Front: ' + name + '\n')
    else:
        mqtt.publishName(name)
        log_file.write('Adding name from admin: ' + name + '\n')
    addHistory('Admin', name, True);
    return str("Done")

def queue_callback(q):
    masterData["queue"]=q;

def queue_low_callback(q):
    masterData["queueLow"]=q;
    

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
        cnt = num_recent_calls(fromNum)
        if cnt < 8:
            mqtt.publishName(textIn)
            msg = "Thanks " + textIn +  "! Based on volume, your name should display in the next " 
            t = 10 * (1+ (math.floor(len(masterData["queue"]) / 13)))
            msg = msg + str(t) + " minutes (best estimate)."
        else: 
            mqtt.publishNameLow(textIn)
            msg = "Thanks " + textIn + "! As you have sent " + str(cnt) + " names in the last"
            msg = msg + " 10 minutes, we will prioritize other names first. "
    else:
        notifyAdmin("Invalid Name on lights: " + textIn)

    addHistory(fromNum, textIn, isValid);
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message(msg)

    return str(resp)

if __name__ == "__main__":
    mqtt.set_queue_callback(queue_callback)
    mqtt.set_queue_low_callback(queue_low_callback)
    addHistory('123-456-7890', 'Test', False);
    addHistory('123-456-7890', 'Test2', False);
    app.run(host='0.0.0.0', port=9999)
