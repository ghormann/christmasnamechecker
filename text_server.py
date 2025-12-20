
# This is the main program for the server and receives
# text messages from twilio and sends them to  the
# home network

from flask import Flask, request, redirect, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from name_validator import NameValidator
from mqtt import MQTTClient
from lib.twillio_lib import create_twillo_clients, findAccount
import datetime
from twilio.rest import Client
import json
import time
import math
import unicodedata

config = json.load(open('greglights_config.json'))
mqtt = MQTTClient()
clients = create_twillo_clients(config)
validator = NameValidator("data/all_names.txt")
validator.addNames("data/custom.txt")
log_file = open("logs/text.log", "a")
masterData = {}
masterData["ready"] = []
masterData["queue"] = []
masterData["admin_song"] = None;
masterData["internal_songs"] = ["Internal_Birthday"]
masterData["queueLow"] = []
masterData["history"] = []
masterData["blocked"] = []
masterData["outPhone"] = []
masterData["fppdWarnings"] = []
masterData["popcorn"] = False
masterData["fppActions"] = []
masterData["timeinfo"] = {"debug": False, "displayHours": False,
                          "newYears": False, "noShow": False, "skipTime": False}
epoch = datetime.datetime.utcfromtimestamp(0)

app = Flask(__name__, static_url_path='')

def num_recent_calls(phone):
    cnt = 0
    for rec in masterData["history"]:
        if rec["phone"] == phone and rec["valid"]:
            diff = time.time() - rec["ts"]
            if (diff < 900):  # 15 min
                cnt += rec["nameCnt"]

    return cnt


def unix_ts(dt):
    return (dt - epoch).total_seconds()


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def addHistory(phone, name, isValid, nameCnt, isBlocked=False):
    rec = {}
    rec["phone"] = phone
    rec["name"] = name
    rec["valid"] = isValid
    rec["blocked"] = isBlocked
    rec["nameCnt"] = nameCnt
    rec["recent"] = num_recent_calls(phone)
    rec["ts"] = time.time()
    masterData["history"].insert(0, rec)
    while (len(masterData["history"]) > 200):
        masterData["history"].pop()


def addOutHistory(phone, message):
    rec = {}
    rec["phone"] = phone
    rec["message"] = message
    rec["ts"] = time.time()
    masterData["outPhone"].insert(0, rec)
    while (len(masterData["outPhone"]) > 20):
        masterData["outPhone"].pop()


def notifyPhone(number, message, clientId="primary"):
    rec = findAccount(config, clientId)
    message = clients[clientId].messages.create(
        to=number,
        from_=rec["fromPhone"],
        body=message)


def notifyAdmin(message):
    rec = findAccount(config)
    message = clients["primary"].messages.create(
        to=config["notifyAdmin"],
        from_=rec["fromPhone"],
        body=message)


@app.route("/queueData", methods=['GET', 'POST'])
def queuedata_reply():
    return json.dumps(masterData, default=json_serial)


@app.route("/favicon.ico", methods=['GET'])
def favicon_reply():
    return redirect("/static/favicon.ico")


@app.route("/status", methods=['GET', 'POST'])
def status_reply():
    return str("Running")


@app.route("/static/<path:path>", methods=['GET'])
def send_static(path):
    return send_from_directory('static', path)


@app.route("/update", methods=['GET', 'POST'])
def update_reply():
    validator.addNames("data/custom.txt")
    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
    log_file.write(ts + "|Reloading names\n")
    log_file.flush()
    return str("loaded custom")


@app.route("/adminReply", methods=['GET'])
def send_text_reply():
    to = request.args.get('to')
    message = request.args.get('message')
    block = request.args.get('block')
    length = int(request.args.get('length'))
    if "yes" == block:
        if not length:
            length = 10
        print("DEBUG: Blocking " + to, flush=True)
        rec = {}
        rec["phone"] = to
        rec["ts"] = time.time()
        rec["length"] = length
        masterData["blocked"].insert(0, rec)

    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
    log_file.write(ts + '|To ' + to + ": " + message + "\n")
    log_file.flush()
    notifyPhone(to, message)
    addOutHistory(to, message)
    return redirect("/static/index.html")


@app.route("/removeBlock", methods=['GET'])
def remove_block():
    phone = request.args.get('phone').strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    print("Looking to remove bock for ", phone)
    newArray = []
    for rec in masterData["blocked"]:
        print("Comparing ", phone, " to ", rec["phone"])
        if phone != rec["phone"]:
            newArray.insert(0, rec)
    masterData["blocked"] = newArray
    print("DEBUG: removeBlock Done", flush=True)
    return redirect("/static/index.html")


def isBlocked(phone):
    newArray = []
    duration = 0
    for rec in masterData["blocked"]:
        diff = (time.time() - rec["ts"]) / 60 # Convert to Minutes
        if diff < rec["length"]:  # Duration of Block
            newArray.insert(0, rec)
        if phone == rec["phone"]:
            duration = round(rec["length"] - diff)

    masterData["blocked"] = newArray
    return duration


@app.route("/setDebug", methods=['GET'])
def set_debug():
    value = request.args.get('debug')
    mqtt.publishDebug(value)
    return redirect("/static/index.html")

@app.route("/forceSong", methods=['GET'])
def set_admin_song():
    value = request.args.get('nextSong')
    mqtt.publishAdminSong(value)
    return redirect("/static/index.html")



@app.route("/setNameGen", methods=['GET'])
def set_name_gen():
    mqtt.publishNameAction("GENERATE")
    return redirect("/static/index.html")


@app.route("/setShortShow", methods=['GET'])
def set_short_show():
    value = request.args.get('short')
    mqtt.publishShortShow(value)
    return redirect("/static/index.html")


@app.route("/setClockDebug", methods=['GET'])
def set_clock_debug():
    value = request.args.get('debug')
    mqtt.publishClockDebug(value)
    return redirect("/static/index.html")

@app.route("/setPopcorn", methods=['GET'])
def set_popcorn():
    value = request.args.get('popcorn')
    mqtt.publishPopcorn(value)
    return redirect("/static/index.html")

@app.route("/setClockSkip", methods=['GET'])
def set_clock_skip():
    value = request.args.get('skip')
    mqtt.publishClockTimeCheck(value)
    return redirect("/static/index.html")


@app.route("/setEnabled", methods=['GET'])
def set_enable():
    value = request.args.get('enabled')
    mqtt.publishEnable(value)
    return redirect("/static/index.html")

def findValidNames(s):
    answer = []
    try:
        s = unicode(s, 'utf-8')
    except NameError:  # unicode is a default on python 3
        pass
        s = unicodedata.normalize('NFD', s)\
            .encode('ascii', 'ignore')\
            .decode("utf-8")

    s = s.upper().strip().replace('&', ' ').replace('!', ' ')
    s = s.replace(' AND ', ' ').replace(',', ' ')
    s = s.replace(".", '').replace("'",'')
   
    if  validator.isValid(s):
        # Approve as whole unit
        answer.append(s);
    else:
        for name in s.split():
            name = cleanName(name)
            if name == "DICK":
                name = "RICHARD"
            if validator.isValid(name):
                answer.append(name)

    return answer

def cleanName(name):
    try:
        name = unicode(name, 'utf-8')
    except NameError:  # unicode is a default on python 3
        pass
        name = unicodedata.normalize('NFD', name)\
            .encode('ascii', 'ignore')\
            .decode("utf-8")

    name = name.upper().strip().replace('&', ' AND ')
    name = ' '.join(name.split())
    return name

@app.route("/addBirthday", methods=['GET'])
def add_birthday_reply():
    name = cleanName(request.args.get('name'))
    mqtt.publishBirthday(name)
    mqtt.publishAdminSong('Internal_Birthday')
    return redirect("/static/index.html")

@app.route("/addName", methods=['GET'])
def add_admin_name_reply():
    name = request.args.get('name')
    pos = request.args.get('pos')
    to = request.args.get('notifyField')
    mqttMessage = {}
    mqttMessage['name'] = cleanName(name)
    mqttMessage['ts'] = unix_ts(datetime.datetime.utcnow())
    mqttMessage['from'] = 'Admin'
    jsonData = json.dumps(mqttMessage, default=json_serial)
    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")

    if len(to) > 8:
        message = "Approved " + \
            mqttMessage['name'] + "! It will appear shortly"
        log_file.write(ts + '|To ' + to + ": " + message + "\n")
        notifyPhone(to, message)
        addOutHistory(to, message)

    if "first" == pos:
        mqtt.publishNameFirst(jsonData)
        log_file.write(ts + '|Adding name from admin: to Front: ' + name + '\n')
        validator.addName(mqttMessage['name'])
    elif "remove" == pos:
        mqtt.removeName(jsonData)
        log_file.write(ts + '|Removing name from admin: to Front: ' + name + '\n')
    elif "purge" == pos:
        mqtt.removeName(jsonData)
        log_file.write(ts + '|Removing name from admin: to Front: ' + name + '\n')
        validator.removeName(mqttMessage['name'])
    else:
        mqtt.publishName(jsonData)
        log_file.write(ts + '|Adding name from admin: ' + name + '\n')
        validator.addName(mqttMessage['name'])
    addHistory('Admin', name, True, 1)
    log_file.flush()
    return redirect("/static/index.html")

def fppd_callback(q):
    warnings = []
    if "warnings" in q:
        warnings = q["warnings"]

    masterData["fppdWarnings"] = warnings

def queue_callback(q):
    masterData["queue"] = q["normal"]
    masterData["queueLow"] = q["low"]
    masterData["ready"] = q["ready"]

def popcorn_callback(as_bool):
    masterData["popcorn"] = as_bool

def fppActions_callback(q):
    q["ts"] = time.time()
    masterData["fppActions"].insert(0, q)
    while (len(masterData["fppActions"]) > 50):
        masterData["fppActions"].pop()

def scheculer_callback(q):
    admin_song = None
    if ("admin_song" in q):
        admin_song = q["admin_song"]

    masterData['admin_song'] = admin_song

def timeinfo_callback(q):
    masterData["timeinfo"] = q

def playlist_callback(q):
    masterData["internal_songs"] = q


@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""

    #  CombinedMultiDict([ImmutableMultiDict([]), ImmutableMultiDict([('ToCountry', 'US'), ('ToState', ''), ('SmsMessageSid', 'Sxxxxxxxxxxxxxxxx'), 
    # ('NumMedia', '0'), ('ToCity', ''), ('FromZip', '45202'), ('SmsSid', 'xxxxxxxxxxxx'), ('FromState', 'OH'), ('SmsStatus', 'received'), 
    # ('FromCity', 'CINCINNATI'), ('Body', 'Doug'), ('FromCountry', 'US'), ('To', '+18881234567'), ('ToZip', ''), ('NumSegments', '1'), ('ReferralNumMedia', '0'), 
    # ('MessageSid', 'SMxxxxxxxxxxxxxxxxx'), ('AccountSid', 'xxxxxxxxxxxxxxxxxx'), ('From', '+15131234567'), 
    # ('ApiVersion', '2010-04-01')])])

    textIn = ' '.join(request.values['Body'].splitlines())
    fromPhone = request.values["To"]
    print(f"Receved message from {fromPhone}", flush=True)
    fromCity = request.values['FromCity']
    fromState = request.values['FromState']
    fromCountry = request.values['FromCountry']
    fromZip = request.values['FromZip']
    fromNum = request.values['From']
    isValid = False
    isNumBlocked=False
    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
    validNames = findValidNames(textIn);
    nameCount = 0
    if validNames:
        isValid=True
        nameCount = len(validNames)

    if "birthday" in textIn.lower():
        notifyAdmin("Birthday: " + textIn)

    jsonData = []
    if isValid:
        for name in validNames:
            mqttMessage = {}
            mqttMessage['name'] = name
            mqttMessage['ts'] = unix_ts(datetime.datetime.utcnow())
            mqttMessage['from'] = fromNum
            jsonData.append(json.dumps(mqttMessage, default=json_serial))

    msg = ts + "|" + str(isValid) + "|" + fromCity + \
        "|" + fromState + "|" + fromCountry
    msg += "|" + fromZip + "|" + fromNum + "|" + textIn

    log_file.write(msg)
    log_file.write("\n")
    log_file.flush()

    msg = "\"" + textIn + \
        "\" isn't a pre-approved first name and has submitted for human review."
    msg += " If approved, you will be notified when it is available."

    blockDuration = isBlocked(fromNum)
    if blockDuration > 0:
        msg = "This phone number has been blocked for " + str(blockDuration) + " minutes due to spam."
        isNumBlocked=True
    elif isValid:
        cnt = num_recent_calls(fromNum)
        if cnt < 8:
            for jMessage in jsonData:
                mqtt.publishName(jMessage)
            msg = "Thanks " + ", ".join(validNames) + "! Based on volume, your name should display in the next "
            t = 10 + (4 * (math.floor(len(masterData["queue"]) / 13)))
            msg = msg + str(t) + " minutes (may be sooner)."
        else:
            for jMessage in jsonData:
                mqtt.publishNameLow(jMessage)
            msg = "Thanks " + ", ".join(validNames) + "! As you have sent " + \
                str(cnt) + " names in the last"
            msg = msg + " 15 minutes, we will prioritize other names first. "
    else:
        notifyAdmin("Invalid Name on lights: " + textIn)

    histMsg = textIn + " [" + ", ".join(validNames) + "]"
    addHistory(fromNum, histMsg, isValid, nameCount, isNumBlocked)
    # Start our TwiML response
    resp = MessagingResponse()

    # Add a message
    resp.message(msg)

    return str(resp)


if __name__ == "__main__":
    mqtt.set_queue_callback(queue_callback)
    mqtt.set_timeinfo_callback(timeinfo_callback)
    mqtt.set_playlist_callback(playlist_callback)
    mqtt.set_scheduler_callback(scheculer_callback)
    mqtt.set_fppd_callback(fppd_callback)
    mqtt.set_popcorn_callback(popcorn_callback)
    mqtt.set_fpp_playlist_action_callback(fppActions_callback)
    addHistory('123-456-7890', 'Test', False, 1)
    addHistory('123-456-7890', 'Test2', False, 1)
    app.run(host='0.0.0.0', port=9999)
