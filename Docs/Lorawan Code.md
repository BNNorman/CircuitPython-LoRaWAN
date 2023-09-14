# LoRaWAN Code.md

The majority of the lorawan handler code is installed in the lib\lorawan folder on the CircuitPython device

# additional libraries

* adafruit_logging.mpy
* adafruit_bus_device
* LogManager.py - see [Docs/Logging.md](../blob/master/Docs/Logging.md)

# lorawan folder

* LoRaWAN sub-folder  : contains the encryption and loRaWAN message handlers.
* SX127x  sub-folder  : contains the code required to drive the RFM9x devices.
* Config.py        : loads the settings.json file
* LorawanHandler.py: this provides a handler for joining, senduing uplinks and receiving downlinks
* MAChandler.py : manages the NVM and handles any MAC commands sent by the TTN server
* Strings.py : just provides capitalised string values to mitigate typos

  
  
