# QuickStart.md

Eager to get going? 

# Step 1 - TTN Console setup

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

# Setp 2 - Device Setup

I developed the code on a Pico but if you are using an ESP32 you need to be aware that it may not have as much spare 
memory is the Pico and that affects which code you should use.

The hardware.md explains the wiring I used - you need the information for editing the settings.json file later.

In the src folder the dev-mpy and dev-py folders contain code which retains the logging used during development. 
the nologging-py and nologging-mpy folders have had all that lovely logging stripped out.

The mpy folders contain precompiled python bytecode using mpcross for the version of CircuitPython I used.

## CircuitPython

The device code was developed with Adafruit CircuitPython 8.2.4. You will need to install it on your device from 
https://circuitpython.org/downloads

The compiled byte codes were prepared using the relevant mpycross compiler. The MPY files will load faster than the 
PY files.

## Raspberry Pi Pico RP2040

copy the code from src/dev-py/lib or src-dev-mpy/lib into your CIRCUITPY/lib folder.

dev-py is recommended whilst testing as it contains logging to file (Useful for me if you need my help).

## ESP32

I used a DOIT ESP32 Development Board for testing.

Due to reduced sram space I recommend you copy the code from src/nologging-py/lib or src/dev-mpy/lib into your 
CIRCUITPY/lib folder. The latter (dev-mpy) includes logging but if space is an issue use the **nologging** mpy code.

## Example Code

Copy all the Example code from the Example folder to the root folder on CIRCUITPY. If using code which provides 
logging **DO NOT** reboot the device till everything is ready because the logging option requires write access to 
the CIRCUITPY root folder and that makes the device read-only to you.

**NOTE** if you are not using logging then you don't need to copy boot.py

## Edit **settings.json**

Settings.json is configured for a pico connected to an RFM95 - See hardware.md for pin numbering.

It is also setup for the EU Frequency Plan. An example for AU_915_928_FSB_2 is included in the AU_Frequency_plan 
folder. You could add the AU plan to settings.json and just change the frequency plan in the TTN section.

You will need to edit this section and put your appeui,deveui and appkey values from the TTN device console in 

		"OTAA": {
            "appeui": [0,0,0,0,0,0,0,0], 
            "deveui": [0,0,0,0,0,0,0,0] ,
            "appkey": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] ,
            "devaddr": [0,0,0,0]
          },
Leave the devaddr entry unchanged. This will force the code to join TTN when you first run it.
The ABP section can be ignored TTN don't recommend using ABP (see https://www.thethingsindustries.
com/docs/devices/abp-vs-otaa).


# First Run

Open up your TTN console so you can monitor activity for your device.

If not using logging (see boot.py) then you can run the testTTN.py program immediately.
If you are using logging, power cycle the device so that boot.py runs and configures the root folder are writeable.

I used Thonny for running the code - later you could make this automatic by editing code.py.

testTTN.py, when run, will try to join the TTN network. You should see log messages for uplinks and downlinks - if you 
within range of a TTN gateway.

If you don't see messages in the TTN you need to trouble shoot why. Start by clearing your NVM (see Utilities)

# Capturing your messages

You need a backend device to capture and use you device messages. TTN provides a number of integrations but my 
example, in the TTN folder, is just using MQTT.




# Best Practises

Read this for a smoother ride ...

https://www.thethingsindustries.com/docs/devices/best-practices/

