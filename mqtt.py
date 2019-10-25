import paho.mqtt.client as paho
import json
import time
import ssl

class MQTTClient:
    """Very simple MQTTClient for publishing approved person names to be displayed on Grid"""
    def __init__(self):
        config = json.load(open('greglights_config.json'))
        client = paho.Client()
        self.client = client
        self.queue_callback = None
        self.queue_low_callback = None
        client.tls_set(ca_certs=config["ca_file"], tls_version=ssl.PROTOCOL_TLSv1_2)
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(config["username"], config["password"])
        client.connect(host=config["host"], port=config["port"])
        client.message_callback_add("/christmas/nameQueue", self.on_queue);
        client.loop_start()
        
    def publishDebug(self, val):
        self.client.publish("/christmas/vote/debug",val,2);

    def publishEnable(self, val):
        self.client.publish("/christmas/setActive",val,2);

    def publishName(self, name):
        self.client.publish("/christmas/personsName", name, 2)    

    def publishNameLow(self, name):
        self.client.publish("/christmas/personsNameLow", name, 2)    

    def publishNameFirst(self, name):
        self.client.publish("/christmas/personsNameFront", name, 2)    

    def removeName(self, name):
        self.client.publish("/christmas/personsNameRemove", name, 2)    

    def on_queue(self, client, userdata, msg):
        q = json.loads(msg.payload.decode('UTF-8'))
        if self.queue_callback:
           self.queue_callback(q)

    def set_queue_callback(self, callback):
        self.queue_callback = callback

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("/christmas/nameQueue")
    client.subscribe("/christmas/nameQueueLow")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

if __name__ == "__main__":
    client = MQTTClient()
    client.publishName("Greg")
    client.publishName("Emily")
    client.publishName("Matt")
    client.publishName("Doug")
    time.sleep(3) 
    
