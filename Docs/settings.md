# Settings.md

The code uses a file named settings.json for its configuration data. The following explains the settings.json file.

Note, if your settings.json is invalid the device will not start properly.

You cannot add comments to JSON in the usual way BUT you can add NOTE key/value pairs, which are not used by the code.

# [BOARD]

This section defines attributes of the MCU board you are using.

Board pins have different names on different MCUs. The Pico uses GPnn whereas the ESP32 uses Dnn. Pin names must be 
quoted strings.

# TX_TIMEOUT

When sending an uplink this is how long to wait for the txDone flag to be set in the RFM IRQ register. If you have 
long payloads and low data rates you should set an appropriate timeout.

In a registered class C device the code will fallback to listening using the RX2 parameters otherwise the RFM will 
be put to sleep. 

# [TTN]

This section contains the default TTN parameters. Settings.json may contain multiple Frequency Plans (e.g.  
EU_863_870_TTN or AU_915_928_FSB_2). The one in use is selected using the "frequency_plan" key.

## rx2_frequency
This is a fixed frequency in the UK

## FcntUp and FCntDn 
These are frame counters used by LoRaWAN to migigate against replay attacks. They should be set to zero 
but will be updated per transmission/reception an stored in NVM.

## auth_mode. TTN strongly recommend using OTAA. Once joined and the keys stored in NVM the device behaves as though 
it was ABP anyway. After a re-join the keys and devaddr will change. That's a good security point. So periodic

** TTN OTAA/ABP Keys

OTAA is highly recommended by TTN, and me.

TTN keys in json MUST be decimal numbers and cannot be hex representations. Hex representations will cause the loading of the config data to fail.

For OTAA the devaddr will be supplied by the TTN server after a successful JOIN. A value of [0,0,0,0] causes the code to re-join.

The following are non-functioning key examples.

This will cause setting.json to fail to load becaause it doesn't like hex numbers.
```
"OTAA": {
            "deveui": [0x43, 0x76, 0x20, 0x49, 0xA0, 0x40, 0xC5, 0xE7],
            "appeui": [0x29, 0x51, 0x00, 0x00, 0xA0, 0x71, 0x01, 0x02],
            "appkey": [0x29, 0x51, 0x03, 0x04, 0xA1, 0x71, 0x002, 0x02, 0xD2, 0x9C, 0x45, 0xC7, 0x04, 0xD2, 0xC0, 0x72],
            "devaddr": [0,0,0,0]
        },
```		
		
This will load ok. But the keys are fake.
```
"OTAA": {
            "deveui": [ 67,118,32,73,161,64,197,231],
            "appeui": [ 41,81,1,0,161,113,10,20],
            "appkey": [41,84,33,44,161,113,22,22,210,156,69,199,42,210,192,114],
            "devaddr": [0,0,0,0]
        },
```		

# [EU_863_870_TTN]

This is the actual frequency plan for the EU region.

## lora_join_freqs and lora_tx_freqs

in EU the join frequencies are limited to the first 3 frequencies from the lora_tx_freqs list. RX1 (downlink) is 
always on the same frequency as the uplink.

After joining the device may transmit on any of the frequencies in the lora_tx_freqs list

The transmission frequency is always randomly selected from the list to reduce the risk of a channel being busy when 
an Uplink is sent.

# [AU_915_928_FSB_2]

You will need to change the rx2_frequency in the [TTN] section.

An example can be found in the AU_frequency_plan folder.







