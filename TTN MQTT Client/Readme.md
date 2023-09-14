# Readme.md

The code in this folder will allow you to receive uplinks and see queued downlinks from/to your device(s).

It uses MQTT to subscribe to uplinks sent to TTN.

This will be run on a PC or Linux device which has access to the internet.

# How to use it

First you need to generate an MQTT API key using the TTN console: Goto Integrations->MQTT and click on 'Generate new API key' and save it in a text file.

Second, edit TTN.toml and add your API key, add your app_id and make sure the ttnBroker is correct for your region.


Then Run TTN.py in a terminal window (CMD on Windows)

```
python TTN.py
``` 

If you use the TTN console to schedule a downlink it should appear in your terminal window (and be logged to downlink.dat)

Now when you start your device using testTTN.py you should see the uplink/downlink scheduled messages appear.