# LoRaWAN Code.md

The majority of the lorawan handler code is installed in the lib\lorawan folder on the CircuitPython device

# additional libraries

If the libraries have been converted using mpcross then the filename extensions will be mpy otherwise just py.

adafruit_logging.(m)py
adafruit_bus_device
LogManager.(m)py

# lorawan folder

LoRaWAN sub-folder  : contains the encryption and loRaWAN message handlers.
SX127x  sub-folder  : contains the code required to drive the RFM9x devices.
Config.(m)py        : loads the settings.json file
LorawanHandler.(m)py: this provides a handler for joining, senduing uplinks and receiving downlinks
