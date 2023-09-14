#!/usr/bin/env python3
"""
ttn-mqtt.py

purpose: to receive MQTT dragino messages from TTN and add them to a log file

The program uses python queue to add jobs (callbacks) to be processed and deals with them
in the main loop.

"""

import time
import json
import paho.mqtt.client as paho
import sys
import toml
import queue
import base64
import binascii

# queue to hold uplinks whilst they are processed
# if you have multiple devices uplinking at the same time
# you could see them fighting for processing
# so we queue them in order of arrival and process them
# in sequence
job_queue=queue.Queue(256)


# get config values and check they exist

configFile = "TTN.toml"
logFile=None # see config
ttnClient= paho.Client()
ttnConnected=False

log=open("downlink.dat","w")

rcConnString={
    0 : "connection successful",
    1 : "Connection refused – incorrect protocol version",
    2 : "Connection refused – invalid client identifier",
    3 : "Connection refused – server unavailable",
    4 : "Connection refused – bad username or password",
    5 : " Connection refused – not authorised"
}


# read in the config file
try:
    config = toml.load(configFile)
    app_id = config["settings"]["app_id"]
    api_key = config["settings"]["api_key"]
    ttnBroker=config["settings"]["ttnBroker"]
    ttnPort=config["settings"]["port"]
    ttnKeepAlive=config["settings"]["keepAlive"]

except KeyError as e:
    raise Exception(f"Config file entry missing: {e}")

except Exception as e:\
    sys.exit(f"{e}")

####################################
#
# message processing
# uplink is a message sent by the device to the TTN server and our app
#


def processUplink(client,obj,msg):
    """Called from run loop"""
    info=json.loads(msg.payload)

    # for debugging
    log.write(json.dumps(info,indent=4))
    log.write("\n##### waiting for new message ######\n")
    log.flush() # to ensure data is recorded

    # extract the frm_payload and f_port number, device_id and application Id
    msg_type=None
    if 'uplink_message' in info:
        msg_type="uplink_message"
    elif 'downlink_queued' in info:
        msg_type="downlink_queued"
    else:
        print("Message type is not a downlink or uplink")
        return

    if msg_type is not None:
        frm_payload = info[msg_type]['frm_payload']
        frm_payload=base64.b64decode(frm_payload)

        f_port=info[msg_type]['f_port']
        device_id=info["end_device_ids"]["device_id"]
        app_id=info["end_device_ids"]["application_ids"]["application_id"]

        # check for a string message
        try:
            frm_payload = frm_payload.decode("ascii")
        except:
            frm_payload=base64.b64decode(frm_payload)

        print(f"msg_type: {msg_type} f_port: {f_port} frm_payload: {frm_payload} device_id: {device_id} app_id: {app_id}")


#####################################
#
# ttn_on_message()
#
# device messages from TTN are queued for handling
#
def ttn_on_message(client, obj,msg):
    global job_queue
    job_queue.put((client,obj,msg))
    #print(f"Added message payload={msg.payload} to job queue")

###################################
#
# ttn_on_connect() callback
#
#
def ttn_on_connect(client,userdata,flags,rc):
    global ttnConnected,ttnClient
    if rc==0:
        print("Connected")
        ttnClient.subscribe("#",0)
        ttnConnected=True
    else:
        print(f"failed to connect  {rcConnString[rc]}")

###################################
#
# ttn_on_subscribe() callback
#
# callbacks from CH mqtt server
#
def ttn_on_subscribe(client,obj,mid,granted_qos):
    print(f"subscribed to TTN server ok granted_qos={granted_qos}")

########################################################
#
# connectToTTN()
#
# create a client and connect it to the broker
# blocks till the first message is received
# which causes ttnClient_connected to be set True


def connectToTTN():
    global ttnClient,app_id,api_key,ttnPort,ttnKeepAlive

    ttnClient.on_message = ttn_on_message
    ttnClient.on_connect = ttn_on_connect
    ttnClient.on_subscribe=ttn_on_subscribe

    ##logging.debug(f"Connecting to TTN with app_id {app_id} api_key {api_key} port {ttnPort} and keepAlives {ttnKeepAlive}")

    print("Connecting to TTN")

    try:
        ttnClient.username_pw_set(app_id, api_key)
        ttnClient.tls_set()  # default certification authority of the system
        ttnClient.loop_start()
        ttnClient.connect(ttnBroker, ttnPort, ttnKeepAlive)

        print("Waiting for TTN on_connect callback")
        return True

    except Exception as e:
        print(f"Exception connecting to TTN: {e}")
        return False
########################################################
# main loop which retrieves jobs from the job_queue
# and passes them to process_job()
########################################################

# connect to the clients
# no point trying TTN if unable to connect to CH broker

if connectToTTN():

    if not ttnConnected:
        print(f"Waiting for mqtt connect")
        start=time.time()
        while not ttnConnected:
            if (time.time()-start)>60:
                print(f"No on_connect callback after 60s")
                exit("connect failed")


    print("Waiting for ttn message callbacks")

    while True:
        # wait nicely
        # process any received messages
        if not job_queue.empty():
            if job_queue.full():
                print("job queue is full, consider increasing its size")
            client,obj,msg=job_queue.get()
            processUplink(client,obj,msg)
        else:
            time.sleep(0.1)

ttnClient.disconnect()



