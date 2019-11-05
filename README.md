# Christmas Name Checker
This implements the webserver for interfacing with Twilo and providing the admin interface. (Yes, the admin interface should be moved to a different repository.) It only impelments http interface w/o any security so it bound to run only on local host with the assumption that apache or ngnix will be used to wrap it.

## Docker
A docker-compose script is included that created a bind to localhost:9999.  The assumption is that Apache or ngnix will work as a proxy to this port adding https and necessary security. 

## Pre-Reqs
* pip install paho-mqtt
* pip install flask
* pip install twilio

## Run
1. source env/bin/activate  (Assuming you created your own local account)
2. nohup python text_server.py 
