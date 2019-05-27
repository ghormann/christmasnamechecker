This implements the webserver for interfacing with Twilo and providing the admin interface. It only impelments http interface w/o any security so it bound to run only on local host with the assumption that apache or ngnix will be used to wrap it.

## Pre-Reqs
* pip install paho-mqtt
* pip install flask
* pip install twilio

## Run
1. source env/bin/activate
2. nohup python text_server.py 
