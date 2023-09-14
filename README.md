# CircuitPython-LoRaWAN

LoRaWAN Spec 1.0.x compliant code using CircuitPython 8.x.x tested on a raspberry Pi Pico with the RFM95 transciever.

The code supports class A and C device classes only.

The main difference between class A and C is that class C devices are always listening for messages on the fixed RX2 
frequency whereas class A devices put the transciever to sleep, after the RX2 window closes, to conserve battery.

To work as class C the device must have joined TTN previously otherwise TTN will not know of its existence and therefore cannot send downlinks (Max of 10 per day).

When the code starts up then, if the device class is C, the RFM9x tranceiver is configured to listen on the RX2 frequency. After sending uplinks the device would be left listening in the RX2 frequency. With class A devices the transceiver will be put to sleep.

Check [Example/testTTN.py](../tree/master/Example/testTTN.py) to see how you should handle class C by checking if a message has been received in your program loop..

Note that CircuitPython handles interrupts using countio which has to be queried (polled) periodically. For that reason this code only polls the RFM9x IRQ register for txDone and rxDone flags. There is no need to connect the transceiver DIO interrupt pins.

# Background

The code is a conversion of my original dragino repo which is available at https://github.com/BNNorman/dragino-1 and runs on a Raspberry Pi wearing a Dragino LoRa/GPS HAT.

During the conversion I have made efforts to try to improve/clean up the code and tested it using CircuitPython V8.2.0 on a RPi connected to an RFM95 transceiver
# Logging

The code makes extensive use of logging to file. See [Docs/Logging.md](../blob/master/Docs/Logging.md)

# Hardware

See [Docs/Hardware.md](../blob/master/Docs/Hardware.md)

See also [Docs/ESP32.md](../blob/master/Docs/ESP32.md)

# Settings file and Cacheing

See also [Docs/Settings.md](../blob/master/Docs/Settings.md)

I would have preffered to keep the configuration file as a TOML but CircuitPython doesn't support sub-sections in TOML files hence I chose to change to a JSON format.

When the code runs for the first time the configuration file (settings.json) is read in and cached in memory. It is 
then saved to NVM so that any changed parameters from TTN Server MAC downlinks are preserved. This is complient with the LoRaWAN spec.

When you next run the code (e.g. after a power cycle and after a previously successful join, the keys stored in NVM are 
used to populate the memory cache so that the end device can continue where it left off.

Note that, once the NVM has been written many of the contents of settings.json are superceded by the stored values. 

The first two bytes of NVM are used to indicate the size of the JSON string stored. If you need to force a re-join, perhaps when testing, you should set the first two bytes to zero or oxffff (unused NVM values). For example:-
```
from microcontroller import nvm
nvm[0:1]=bytearray([0,0])
```
See Utilities.

See [Docs/Settings.md](../blob/master/Docs/Settings.md) for help on the settings.json file.

# Newbies to TTN & LoRaWAN?
This code records the transmission duration each time so you can use that to adhere to legal duty cycles and TTNs' Fair Use Policy. The example code testTTN.py sticks to these limits and shows one way to do it. You can use this site to calculate the expected air time for your planned payload. https://avbentem.github.io/airtime-calculator/ttn/eu868.

The calculator also indicates how many messages per hour can be sent at different SF values. The nearer your device is to a gateway the lower your SF can be and the faster your transmissions will be. Hence, more transmissions per hour but keep in mind the FUP and Duty Cycle limits discussed below.

Remember that you can reduce your playload size by 1 byte if you use port numbers to convey information. At SF11 this can make an 80ms reduction in transmission time.

## Duty Cycle
You need to understand that there is, in some countries, a legal duty cycle limit. In the UK it is 1% which means you can transmit for 1 second then you have to wait 99 seconds before you transmit again. The law will not take kindly if you exceed that. Reduce your payload size to,possibly, allow more frequent transmissions.
## Fair Use Policy (FUP)
TTN has a limit of 30s uplink transmission time per 24 hour period. You should endeavor to stay within that time. If you can't then TTN/LoRaWAN is not for you.
## Downlinks
TTN requires that you don't request more than 10 downlinks per day. If a downlink contains a user downlink message and you have configured a dowlink callback method your code will receive the payload and port information. See Example\testTTN.py.
## Gateways
These have to obey the regional duty cycle. If too many downlinks are being sent by all users it means the gateway isn't listening for uplinks.
## TTN
You will have to set up an account on the TTN website for your region so that you can create devices which can then join the network.
## RX Windows
Following an uplink the server may, or may not, send you a downlink message. This code switches to receive mode immediately after transmission then waits for the RX1 window to close then switches to RX2. The RX1 and RX2 frequencies are defined in the Frequency Plans for the various regions.
## OTAA or ABP?
TTN recommend using OTAA over ABP always.
When you JOIN TTN using OTAA the server generates a new devaddr,nwkskey and appskey and restarts the message counter. With ABP these key values are fixed. 

With OTAA if you suspect foul play you can force a reJOIN which invalidates the previous session keys. One way to do this remotely would be add code for a special downlink which tells your code to wipe the NVM data and reboot thus forcing a new join.

## Limiting Uplink Size
Each uplink packet includes a port number, which can be set when you send a message. By default the port number is 1. Port 0 is reserved for downlink MAC commands. Port numbers above 232 are reserved for TTN testing - not you!
The port number is included in every transmission so can be used to reduce your payload data length by 1 byte if you want your app to route messages using if-else or switch (C) statements in your backend.
## Message Counter
Each uplink message contains a 2 byte counter (FCntUp) which is a protection against replay attacks. The counter is incremented for each message. If another message arrives at the TTN server with a lower value counter then the TTN server will ignore it till it exceeds the last counter value.

If you cause the code to rejoin TTN then the server counter is reset to zero. Rejoining means your device will get a new devaddr,nwkskey and appskey.



