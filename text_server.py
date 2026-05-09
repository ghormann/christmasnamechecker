
# This is the main program for the server and receives
# text messages from twilio and sends them to  the
# home network

from flask import Flask, request, redirect, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from name_validator import NameValidator
from mqtt import MQTTClient, MQTTEventHandler
from lib.twillio_lib import create_twillo_clients, findAccount
import datetime
import threading
import logging
from twilio.rest import Client
import json
import os
import time
import math
import unicodedata

CACHE_PATH = "cache/state.json"


def load_cache(path=CACHE_PATH):
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            "history": data.get("history", []),
            "blocked": data.get("blocked", []),
            "outPhone": data.get("outPhone", []),
        }
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, Exception) as e:
        logging.warning("Cache load failed: %s", e)
        return None


def save_cache(data, path=CACHE_PATH):
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except Exception as e:
        logging.warning("Cache save failed: %s", e)


with open('greglights_config.json') as f:
    config = json.load(f)

logging.basicConfig(
    filename="logs/text.log",
    filemode='a',
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

clients = create_twillo_clients(config)
validator = NameValidator("data/all_names.txt")
validator.addNames("data/custom.txt")

data_lock = threading.RLock()
masterData = {}
masterData["buttons"] = {
    "A": ["Alpha", "Angel", "Aspen"],
    "B": ["Buddy", "Bailey", "Bingo"]
}
masterData["ready"] = []
masterData["queue"] = []
masterData["admin_song"] = None
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


class AppMQTTHandler(MQTTEventHandler):
    def on_queue(self, q):
        with data_lock:
            masterData["queue"] = q["normal"]
            masterData["queueLow"] = q["low"]
            masterData["ready"] = q["ready"]

    def on_timeinfo(self, q):
        with data_lock:
            masterData["timeinfo"] = q

    def on_playlist(self, q):
        with data_lock:
            masterData["internal_songs"] = q

    def on_scheduler_status(self, q):
        with data_lock:
            masterData["admin_song"] = q.get("admin_song")

    def on_fppd(self, q):
        with data_lock:
            masterData["fppdWarnings"] = q.get("warnings", [])

    def on_popcorn(self, q):
        with data_lock:
            masterData["popcorn"] = q

    def on_fpp_playlist_action(self, q):
        with data_lock:
            q["ts"] = time.time()
            masterData["fppActions"].insert(0, q)
            while len(masterData["fppActions"]) > 50:
                masterData["fppActions"].pop()

    def on_buttons(self, q):
        with data_lock:
            masterData["buttons"] = q


def _cache_saver_thread():
    while True:
        time.sleep(60)
        with data_lock:
            data = {
                "history": list(masterData["history"]),
                "blocked": list(masterData["blocked"]),
                "outPhone": list(masterData["outPhone"]),
            }
        save_cache(data)


mqtt = MQTTClient(handler=AppMQTTHandler())

_cached = load_cache()
if _cached:
    masterData["history"] = _cached["history"]
    masterData["blocked"] = _cached["blocked"]
    masterData["outPhone"] = _cached["outPhone"]
    logger.info("Cache restored: %d history, %d blocked, %d outPhone",
                len(_cached["history"]), len(_cached["blocked"]), len(_cached["outPhone"]))

_saver = threading.Thread(target=_cache_saver_thread, daemon=True, name="cache-saver")
_saver.start()


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
    with data_lock:
        rec = {
            "phone": phone,
            "name": name,
            "valid": isValid,
            "blocked": isBlocked,
            "nameCnt": nameCnt,
            "recent": num_recent_calls(phone),
            "ts": time.time(),
        }
        masterData["history"].insert(0, rec)
        while len(masterData["history"]) > 200:
            masterData["history"].pop()


def addOutHistory(phone, message):
    with data_lock:
        rec = {"phone": phone, "message": message, "ts": time.time()}
        masterData["outPhone"].insert(0, rec)
        while len(masterData["outPhone"]) > 20:
            masterData["outPhone"].pop()


def notifyPhone(number, message, clientId="primary"):
    rec = findAccount(config, clientId)
    clients[clientId].messages.create(
        to=number,
        from_=rec["fromPhone"],
        body=message)


def notifyAdmin(message):
    rec = findAccount(config)
    clients["primary"].messages.create(
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
    logger.info(ts + "|Reloading names")
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
        with data_lock:
            masterData["blocked"].insert(0, {
                "phone": to,
                "ts": time.time(),
                "length": length,
            })

    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
    logger.info(ts + '|To ' + to + ": " + message)
    notifyPhone(to, message)
    addOutHistory(to, message)
    return redirect("/static/index.html")

@app.route("/", methods=['GET'])
def index():
    return redirect("/static/index.html")

@app.route("/removeBlock", methods=['GET'])
def remove_block():
    phone = request.args.get('phone').strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    print("Looking to remove block for ", phone)
    with data_lock:
        masterData["blocked"] = [rec for rec in masterData["blocked"] if rec["phone"] != phone]
    print("DEBUG: removeBlock Done", flush=True)
    return redirect("/static/index.html")


def _prune_blocked():
    """Remove expired block entries from masterData."""
    with data_lock:
        masterData["blocked"] = [
            rec for rec in masterData["blocked"]
            if (time.time() - rec["ts"]) / 60 < rec["length"]
        ]


def isBlocked(phone):
    _prune_blocked()
    with data_lock:
        for rec in masterData["blocked"]:
            if rec["phone"] == phone:
                diff = (time.time() - rec["ts"]) / 60
                return round(rec["length"] - diff)
    return 0


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
    # Normalize unicode to ASCII equivalents
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode("utf-8")

    s = s.upper().strip().replace('&', ' ').replace('!', ' ')
    s = s.replace(' AND ', ' ').replace(',', ' ')
    s = s.replace(".", '').replace("'",'')

    if  validator.isValid(s):
        # Approve as whole unit
        answer.append(s)
    else:
        for name in s.split():
            name = cleanName(name)
            if name == "DICK":
                name = "RICHARD"
            if validator.isValid(name):
                answer.append(name)

    return answer

def cleanName(name):
    # Normalize unicode to ASCII equivalents
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8")
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
        logger.info(ts + '|To ' + to + ": " + message)
        notifyPhone(to, message)
        addOutHistory(to, message)

    if "first" == pos:
        mqtt.publishNameFirst(jsonData)
        logger.info(ts + '|Adding name from admin: to Front: ' + name)
        validator.addName(mqttMessage['name'])
    elif "remove" == pos:
        mqtt.removeName(jsonData)
        logger.info(ts + '|Removing name from admin: to Front: ' + name)
    elif "purge" == pos:
        mqtt.removeName(jsonData)
        logger.info(ts + '|Removing name from admin: to Front: ' + name)
        validator.removeName(mqttMessage['name'])
    else:
        mqtt.publishName(jsonData)
        logger.info(ts + '|Adding name from admin: ' + name)
        validator.addName(mqttMessage['name'])
    addHistory('Admin', name, True, 1)
    return redirect("/static/index.html")

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""

    #  CombinedMultiDict([ImmutableMultiDict([]), ImmutableMultiDict([('ToCountry', 'US'), ('ToState', ''), ('SmsMessageSid', 'Sxxxxxxxxxxxxxxxx'),
    # ('NumMedia', '0'), ('ToCity', ''), ('FromZip', '45202'), ('SmsSid', 'xxxxxxxxxxxx'), ('FromState', 'OH'), ('SmsStatus', 'received'),
    # ('FromCity', 'CINCINNATI'), ('Body', 'Doug'), ('FromCountry', 'US'), ('To', '+18881234567'), ('ToZip', ''), ('NumSegments', '1'), ('ReferralNumMedia', '0'),
    # ('MessageSid', 'SMxxxxxxxxxxxxxxxxx'), ('AccountSid', 'xxxxxxxxxxxxxxxxxx'), ('From', '+15131234567'),
    # ('ApiVersion', '2010-04-01')])])

    textIn = ' '.join(request.values['Body'].splitlines())
    fromCity = request.values['FromCity']
    fromState = request.values['FromState']
    fromCountry = request.values['FromCountry']
    fromZip = request.values['FromZip']
    fromNum = request.values['From']
    isValid = False
    isNumBlocked=False
    ts = datetime.datetime.now().strftime("%d-%B-%Y %I:%M%p")
    validNames = findValidNames(textIn)
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

    logger.info(msg)

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
            with data_lock:
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
    if not masterData["history"]:
        addHistory('123-456-7890', 'Test', False, 1)
        addHistory('123-456-7890', 'Test2', False, 1)
    app.run(host='0.0.0.0', port=9999)
