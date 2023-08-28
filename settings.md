# Settings.md

The code uses a file named settings.json for it's configuration data.

CircuitPython does not support heirarchical TOML so the settings file was converted to JSON.

Note, that when the CircuitPython device is first started the settings.json contents are read and used to join to TTN. TTN may change some parameters using MAC commands. 
These are cached in NVM and used instead of settings.json on the next restart/reboot.

If changes are made to the TTN section of settings.json then you can clean out the NVM to force the code to rejoin TTN by using the wipeNVM.py program. 


** TTN OTAA/ABP Keys

OTAA is highly recommended by TTN.

TTN keys in json MUST be decimal numbers and cannot be hex representations. Hex representations will cause the loading of the config data to fail.

For OTAA the devaddr will be supplied by the TTN server after a successful JOIN. A value of [0,0,0,0] causes the code to re-join.

The following are non-functioning key examples.

This will cause setting.json to fail to load...
```
"OTAA": {
            "deveui": [0x43, 0x76, 0x20, 0x49, 0xA0, 0x40, 0xC5, 0xE7],
            "appeui": [0x29, 0x51, 0x00, 0x00, 0xA0, 0x71, 0x01, 0x02],
            "appkey": [0x29, 0x51, 0x03, 0x04, 0xA1, 0x71, 0x002, 0x02, 0xD2, 0x9C, 0x45, 0xC7, 0x04, 0xD2, 0xC0, 0x72],
            "devaddr": [0,0,0,0]
        },
```		
		
This will load ok.
```
"OTAA": {
            "deveui": [ 67,118,32,73,161,64,197,231],
            "appeui": [ 41,81,0,0,161,113,1,2],
            "appkey": [41,81,3,4,161,113,2,2,210,156,69,199,4,210,192,114],
            "devaddr": [0,0,0,0]
        },
```		
* MAC caching

The settings.json file contains the initial settings for the frequency plan etc. When the code starts up it checks NVM to see if any data has been previously stored. If so then the stored values supercede those in settings.json.

During normal operation the TTN server may send downlinks containing new RX/TX settings. These will be updated in NVM and so remembered for the next power cycle.

The length of available NVM varies with device. The RPi pico has 4Kb whereas the DOIT ESP32 Devkit V1 has 8Kb. The length of NVM can be determined with the following code:-

```
from microcontroller import nvm
print(len(nvm[0:-1]))
```

A typical cache will use less than 1Kb of NVM.









