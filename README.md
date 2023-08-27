# CircuitPython-LoRaWAN
CircuitPython LoRaWAN code to work with the HopeRF RFM95 

# Introduction

This is a conversion of my dragino repo to work with Adafruit CircuitPython 8.2.0 on 2023-07-05; Raspberry Pi Pico with rp2040 connected to a HopeRF RFM95 module. The ESP32 MAY work but has less available memory and so mpcross needs to be used to shrink the files.

The original dragino repo is available at https://github.com/BNNorman/dragino-1 and runs on a Raspberry Pi wearing a Dragino LoRa/GPS HAT.

During conversion I have made efforts to try to improve/clean up the code.

The code is compliant with LoRa Specification 1.0.2.

# Parameter Cacheing

I would have preffered to keep the configuration file as a TOML but CircuitPython doesn't support sub-sections in TOML files hence I chose to change to a JSON format.

When the code runs for the first time the configuration file (settings.json) is read in , cached, and provides the information required for the device to join TTN. The communication parameters are then cached and saved to NVM (Cacheing is a requirement of the LoRa Specification). If the TTN server sends us MAC commands to modify behaviour (output power, sf etc) then those parameters are updated in the cache and the NVM is updated.

When you next run the code, after a successful join, the keys stored in NVM are used to populate the cache so that the end device can continue where it left off after a shutdown.

Note that, once the NVM has been written the contents of settings.json are largely ignored.

The first two bytes of NVM are used to indicate the size of the JSON string stored. If you need to force a re-join, perhaps when testing, you should set the first two bytes to zero or oxffff (unused NVM values). For example:-
```
from microcontroller import nvm
nvm[0:1]=bytearray([0,0])
```

# Logging
The development code uses a lot of logging to file which requires that you remount your filesystem rw. In boot.py add the following:-
```
import storage
storage.remount("/",False)
```
then reboot your device.

The logging library can be found here:-
```
[BNNorman/CircuitPython-logging-manager](https://github.com/BNNorman/CircuitPython-logging-manager)https://github.com/BNNorman/CircuitPython-logging-manager)
```
Note that it extends adafruit_logging by adding a label immediately after the timestamp as shown in this snippet. If you look in testTTN.py you can see how I configure all my library modules to allow ALL levels of log messages (LogMan.NOTSET) to change to logging only LogMan.WARNING or LogMan.CRITICAL.

Not that my LogManager code allows sub-modules to log to the same file. The adafruit_logging module does not do that.

```
3735.885: JOIN_ACCEPT DEBUG - Loading
3736.575: LorawanHandler DEBUG - Loading
3737.593: board_config INFO - Configuring for board id=raspberry_pi_pico
3738.405: MAChandler INFO - Loading
3738.835: LorawanHandler DEBUG - init starting
3738.979: LorawanHandler DEBUG - Get board config
3739.096: LorawanHandler DEBUG - LorawanHandler calling BOARD setup
3739.210: raspberry_pi_pico INFO - Setting up MCU raspberry_pi_pico
3739.325: raspberry_pi_pico INFO - SPI Pins read from settings
3739.443: raspberry_pi_pico INFO - SPI device setup completed.
3740.688: raspberry_pi_pico INFO - MCU Device setup finished
3740.811: LoraRadio INFO - resetting RFM9x
3740.940: LoraRadio INFO - After reset() Mode : RX_LF
3741.065: LoraRadio INFO - Set Mode : FSK_STDBY
3741.208: LoraRadio INFO - Set Mode : SLEEP
3741.334: LorawanHandler DEBUG - LoRaRadio has been setup
3741.459: MAChandler DEBUG - MAC_Commands init
3741.585: MAChandler INFO - Frequency plan is EU_863_870_TTN
3741.711: MAChandler INFO - NVM is empty. Could be first run.
3741.963: MAChandler INFO - NVM not set. Using [TTN] section as defaults
3742.084: MAChandler INFO - Setting default MAC cache values using user config values
3742.208: MAChandler INFO - loading frequency plan
3742.330: MAChandler INFO - Frequency Plan is EU_863_870_TTN
```
# Newbies to TTN & LoRaWAN?
This code records the transmission duration each time so you can use that to adhere to legal duty cycles and TTNs' Fair Use Policy. The example code testTTN.py sticks to these limits and shows one way to do it.
## Duty Cycle
You need to understand that there is, in some countries, a legal duty cycle limit. In the UK it is 1% which means you can transmit for 1 second then you have to wait 99 seconds before you transmit again. The law will not take kindly if you exceed that.
## Fair Use Policy (FUP)
TTN has a limit of 30s uplink transmission time per 24 hour period. 
## Downlinks
TTN requires that you don't request more than 10 downlinks per day.
## Gateways
These have to obey the regional duty cycle
## TTN
You will have to set up an account on the TTN for your region so that you can create devices which can then join the network.
## RX Windows
Following an uplink the server may, or may not, send you a message. This code switches to receive mode immediately after transmission then waits for the RX1 window to close then switches to RX2. The RX1 and RX2 frequencies are defined in the Frequency Plans for the various regions.
# Limiting Uplink Size
Each uplink packet includes a port number, which can be set when you send a message. By default the port number is 1. Port 0 is reserved for downlink MAC commands. Port numbers above 232 are reserved for TTN testing - not you!
The port number is included in every transmission so can be used to reduce your payload data length by 1 byte if you want your app to route messages using if-else or switch (C) statements in your backend.
# Message Counter
Each uplink message contains a 2 byte counter which is a protection against replay attacks. The counter is incremented for each message. If another message arrives at the TTN server with a lower value counter then the TTN server will ignore it till it exceeds the last counter value.

If you cause the code to rejoin TTN then the server counter is reset to zero. Rejoining means your device will get a new devaddr,nwkskey and appskey.

# Interrupts and Polling

CircuitPython does not play nicely with interrupts. For that reason this code Polls the RFM95 interrupt register for TxDone and RxDone. Since the RX1 window and RX2 windows are approximately 6 seconds you will have to factor that into your sensor reading frequency.

# Development Hardware

Here is my RPi Pico connected to an HopeRF RFM95 which I used for testing

