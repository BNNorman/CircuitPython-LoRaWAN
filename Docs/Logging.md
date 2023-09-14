# Logging

Logging to file is possible and was used during development for bug catching. It relies on my LogManager module to ensure that log messages are all passed to the same stream and end up in one file.

You can find my logging extension to adafruit_logging here https://github.com/BNNorman/CircuitPython-logging-manager

The filesystem on a CiruitPython device is read-only to programs by default, even though you can copy files to/from USB. 
To enable logging the filesystem is made writeable with the following command placed in boot.py :-

```
import storage
storeage.remount("/",True)
```

## Managing logging level

If the submodules are cross compiled to MPY bytecode then changing the logging level would require you to edit the PY files, cross compile to MPY then upload the files to the device. However, my LogManager provides a method to set all imported modules to the same log level. See Example\testTTN.py.

## Partial Log Example

The log contains lines formatted this way:-

```
timestamp module log_level message
```

To limit the number of messages you can set the log level in your code (see testTTN.py) or you can work through the sources and remove all logging, though setting the log level to CRITICAL+1 would have the same effect.


```

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
