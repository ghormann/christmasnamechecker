FROM python:3

WORKDIR /usr/src/app

RUN pip install --no-cache-dir paho-mqtt
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir twilio

COPY . .

CMD [ "python", "./text_server.py" ]
