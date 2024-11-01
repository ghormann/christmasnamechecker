import paho.mqtt.client as paho
import json
import time
import ssl

class MQTTClient:
    """Very simple MQTTClient for publishing approved person names to be displayed on Grid"""
    def __init__(self):
        config = json.load(open('greglights_config.json'));
        client = paho.Client();
        self.client = client;
        self.queue_callback = None;
        self.timeinfo_callback = None;
        self.queue_low_callback = None;
        self.playlist_callback = None;
        self.scheduler_callback = None;
        self.fppd_callback = None;
        #client.tls_set(ca_certs=config["ca_file"], tls_version=ssl.PROTOCOL_TLSv1_2)
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(config["username"], config["password"])
        client.connect(host=config["host"], port=config["port"])
        client.message_callback_add("/christmas/nameQueue", self.on_queue);
        client.message_callback_add("/christmas/timeinfo", self.on_timeinfo);
        client.message_callback_add("/christmas/scheduler/all_playlist_internal", self.on_playlist);
        client.message_callback_add("/christmas/scheduler/status", self.on_scheduler_status);
        client.message_callback_add("/christmas/falcon/player/fpp2/fppd_status", self.on_main_fpp);
        client.loop_start()
        
    def publishHealth(self):
        self.client.publish("/christmas/namechecker/health",time.time(),2)

    def publishNameAction(self, val):
        self.client.publish("/christmas/nameAction",val,2)

    def publishDebug(self, val):
        self.client.publish("/christmas/vote/debug",val,2);

    def publishAdminSong(self, val):
        self.client.publish("/christmas/scheduler/setAdminSong",val,2)

    def publishClockDebug(self, val):
        self.client.publish("/christmas/clock/setDebug",val,2);

    def publishShortShow(self, val):
        self.client.publish("/christmas/vote/setShortList",val,2);

    def publishClockTimeCheck(self, val):
        self.client.publish("/christmas/clock/setTimeCheck",val,2);

    def publishEnable(self, val):
        self.client.publish("/christmas/setActive",val,2);

    def publishName(self, name):
        self.client.publish("/christmas/personsName", name, 2)    

    def publishNameLow(self, name):
        self.client.publish("/christmas/personsNameLow", name, 2)    

    def publishNameFirst(self, name):
        self.client.publish("/christmas/personsNameFront", name, 2)    

    def publishBirthday(self, name):
        self.client.publish("/christmas/nameBirthday", name, 2)    

    def removeName(self, name):
        self.client.publish("/christmas/personsNameRemove", name, 2)    

    def on_queue(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.queue_callback:
           self.queue_callback(q)
        self.publishHealth()

    def on_timeinfo(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.timeinfo_callback:
           self.timeinfo_callback(q)

    def on_playlist(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.playlist_callback:
           self.playlist_callback(q)

    def on_scheduler_status(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.scheduler_callback:
           self.scheduler_callback(q)

    def on_main_fpp(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.fppd_callback:
            self.fppd_callback(q)

    def set_fppd_callback(self, callback):
        self.fppd_callback = callback

    def set_queue_callback(self, callback):
        self.queue_callback = callback

    def set_timeinfo_callback(self, callback):
        self.timeinfo_callback = callback

    def set_playlist_callback(self, callback):
        self.playlist_callback = callback

    def set_scheduler_callback(self, callback):
        self.scheduler_callback = callback

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("/christmas/nameQueue")
    client.subscribe("/christmas/timeinfo")
    client.subscribe("/christmas/scheduler/all_playlist_internal")
    client.subscribe("/christmas/scheduler/status")
    client.subscribe("/christmas/falcon/player/fpp2/fppd_status")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("WARNING: Unhandled topic: "+ str(msg.topic) + " "+str(msg.payload))

if __name__ == "__main__":
    client = MQTTClient()
    client.publishName("Greg")
    client.publishName("Emily")
    client.publishName("Matt")
    client.publishName("Doug")
    time.sleep(3) 
    
