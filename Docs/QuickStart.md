# QuickStart.md

Eager to get going? 

## Step 1 - TTN Console setup

1 Create an account on The Thngs Stack Community Edition. 

2 From your console **Go to applications**

3 Press the button **+ Create Application**

4 Think of an **application ID** and make a note of it.

5 Press **+ Register End Device**

Record the appeui, deveui and appkey. These should be MSB first and converted to decimal because json doesn't like 
hex numbers and CircuitPython doesn't handle TOML with subsections.

This short python snippet will convert a hex list to a decimal number list.
```
appeui=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]
print(list(appeui))
```

Now you need to setup your device and get it to join TTN in order to obtain the appskey used to decode message payloads

## Step 2 - Device Setup

I developed the code on a Pico but if you are using an ESP32 you need to be aware that it may not have as much spare 
memory is the Pico and that affects which code you should use.

The hardware.md explains the wiring I used - you need the information for editing the settings.json file later.

In the src folder the dev-mpy and dev-py folders contain code which retains the logging used during development. 
the nologging-py and nologging-mpy folders have had all that lovely logging stripped out.

The mpy folders contain precompiled python bytecode using mpcross for the version of CircuitPython I used.

# CircuitPython

The device code was developed with Adafruit CircuitPython 8.2.4. You will need to install it on your device from 
https://circuitpython.org/downloads

## lib

copy the files and folders from src/lib into your CIRCUITPY/lib folder.

## Example Code

Copy all the Example code from the Example folder to the root folder on CIRCUITPY. You will need to reboot your device later so that testTTN.py can create a log file.

## Edit **settings.json**

Settings.json is configured for a pico connected to an RFM95 - See [Docs/Hardware.md](../master/Docs/Hardware.md) for pin numbering.

It is also setup for the EU_868_870_TTN Frequency Plan. An example for AU_915_928_FSB_2 is included in the Frequency_plan 
folder. To use the AU plan delete the two sections [TTN] and [EU_868_870_TTN] from settings.json and paste in the AU plan.

You will need to edit this section and put your appeui,deveui and appkey values from the TTN device console in 

		"OTAA": {
            "appeui": [0,0,0,0,0,0,0,0], 
            "deveui": [0,0,0,0,0,0,0,0] ,
            "appkey": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] ,
            "devaddr": [0,0,0,0]
          },
Leave the devaddr entry unchanged. This will force the code to join TTN when you first run it.
The ABP section can be ignored TTN don't recommend using ABP (see https://www.thethingsindustries.com/docs/devices/abp-vs-otaa).


# First Run

Open up your TTN console so you can monitor activity for your device.

Power cycle the device so that boot.py runs and configures the root folder as writeable.

I used Thonny for running the code - later you could make this automatic by editing code.py to do this:-
```
import testTTN
```

testTTN.py, when run, will try to join the TTN network. You should see TTN console log messages for uplinks and downlinks in the TTN console - if you are within range of a TTN gateway. In particular you should see a JOIN REQUEST arriving from your device.

If you don't see messages in the TTN console you need to trouble shoot why. You could be out of range of a gateway or too close. The latter will swamp the gateway receiver and garbage the signals. If you have your own gateway make sure you have a wall plus 15 feet of space between your device and the gateway. Mine shows a 55db signal strength and connects every time at that range.

# Capturing your uplink messages

You need a backend device to capture and use you device messages. TTN provides a number of integrations but [my 
example](../master/Example/TTN.py) is just using MQTT and runs on Windows and should also run on linux.


# Best Practises

Read this for a smoother ride ...

https://www.thethingsindustries.com/docs/devices/best-practices/

