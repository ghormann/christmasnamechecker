import paho.mqtt.client as paho
import json
import time


class MQTTEventHandler:
    """Base class for handling incoming MQTT events. Override methods as needed."""
    def on_queue(self, q): pass
    def on_timeinfo(self, q): pass
    def on_playlist(self, q): pass
    def on_scheduler_status(self, q): pass
    def on_fppd(self, q): pass
    def on_popcorn(self, q): pass
    def on_fpp_playlist_action(self, q): pass
    def on_buttons(self, q): pass
    def on_name_estimate(self, q): pass


class MQTTClient:
    """Very simple MQTTClient for publishing approved person names to be displayed on Grid"""
    def __init__(self, handler=None):
        with open('greglights_config.json') as f:
            config = json.load(f)
        self.handler = handler or MQTTEventHandler()
        client = paho.Client()
        self.client = client
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.username_pw_set(config["username"], config["password"])
        client.connect(host=config["host"], port=config["port"])
        client.message_callback_add("/christmas/nameQueue", self._on_queue)
        client.message_callback_add("/christmas/timeinfo", self._on_timeinfo)
        client.message_callback_add("/christmas/scheduler/all_playlist_internal", self._on_playlist)
        client.message_callback_add("/christmas/scheduler/status", self._on_scheduler_status)
        client.message_callback_add("/christmas/falcon/player/fpp2/fppd_status", self._on_main_fpp)
        client.message_callback_add("/christmas/clock/popcorn", self._on_popcorn)
        client.message_callback_add("/christmas/scheduler/button_mapping", self._on_buttons)
        client.message_callback_add("/christmas/scheduler/fpp_playlist_action", self._on_fpp_playlist_action)
        client.message_callback_add("/christmas/scheduler/name_estimate", self._on_name_estimate)
        client.loop_start()

    def publishPopcorn(self, val):
        self.client.publish("/christmas/clock/setPopcorn", val, 2)

    def publishHealth(self):
        self.client.publish("/christmas/namechecker/health", time.time(), 2)

    def publishNameAction(self, val):
        self.client.publish("/christmas/nameAction", val, 2)

    def publishDebug(self, val):
        self.client.publish("/christmas/vote/debug", val, 2)

    def publishAdminSong(self, val):
        self.client.publish("/christmas/scheduler/setAdminSong", val, 2)

    def publishClockDebug(self, val):
        self.client.publish("/christmas/clock/setDebug", val, 2)

    def publishShortShow(self, val):
        self.client.publish("/christmas/vote/setShortList", val, 2)

    def publishClockTimeCheck(self, val):
        self.client.publish("/christmas/clock/setTimeCheck", val, 2)

    def publishEnable(self, val):
        self.client.publish("/christmas/setActive", val, 2)

    def publishTunnelEnable(self, val):
        self.client.publish("/christmas/setActive/tunnel", val, 2)

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

    def _on_buttons(self, client, userdata, msg):
        self.handler.on_buttons(json.loads(msg.payload.decode('UTF-8')))

    def _on_queue(self, client, userdata, msg):
        self.handler.on_queue(json.loads(msg.payload.decode('UTF-8')))
        self.publishHealth()

    def _on_timeinfo(self, client, userdata, msg):
        self.handler.on_timeinfo(json.loads(msg.payload.decode('UTF-8')))

    def _on_playlist(self, client, userdata, msg):
        self.handler.on_playlist(json.loads(msg.payload.decode('UTF-8')))

    def _on_scheduler_status(self, client, userdata, msg):
        self.handler.on_scheduler_status(json.loads(msg.payload.decode('UTF-8')))

    def _on_main_fpp(self, client, userdata, msg):
        self.handler.on_fppd(json.loads(msg.payload.decode('UTF-8')))

    def _on_fpp_playlist_action(self, client, userdata, msg):
        self.handler.on_fpp_playlist_action(json.loads(msg.payload.decode('UTF-8')))

    def _on_name_estimate(self, client, userdata, msg):
        self.handler.on_name_estimate(json.loads(msg.payload.decode('UTF-8')))

    def _on_popcorn(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        print("Popcorn message received: " + str(q))
        self.handler.on_popcorn(q)

    def _on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        # Subscribing in on_connect means subscriptions are renewed on reconnect
        client.subscribe("/christmas/nameQueue")
        client.subscribe("/christmas/timeinfo")
        client.subscribe("/christmas/clock/popcorn")
        client.subscribe("/christmas/scheduler/all_playlist_internal")
        client.subscribe("/christmas/scheduler/status")
        client.subscribe("/christmas/falcon/player/fpp2/fppd_status")
        client.subscribe("/christmas/scheduler/fpp_playlist_action")
        client.subscribe("/christmas/scheduler/button_mapping")
        client.subscribe("/christmas/scheduler/name_estimate")

    def _on_message(self, client, userdata, msg):
        print("WARNING: Unhandled topic: " + str(msg.topic) + " " + str(msg.payload))


if __name__ == "__main__":
    client = MQTTClient()
    client.publishName("Greg")
    client.publishName("Emily")
    client.publishName("Matt")
    client.publishName("Doug")
    time.sleep(3)
