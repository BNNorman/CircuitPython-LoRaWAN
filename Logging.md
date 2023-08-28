# Logging

Logging to file is possible and was used during development for bug catching. It relies on my LogManager module to ensure that log messages are all passed to the same stream and end up in one file.

You can find my logging extension to adafruit_logging here https://github.com/BNNorman/CircuitPython-logging-manager

The filesystem on a CiruitPython device is read-only to programs by default. It is possible to make it writeable with the command placed in boot.py :-

```
import storage
storeage.remount("/",True)
```


## Managing logging level

If the submodules are cross compiled to MPY bytecode then changing the logging level would require you to edit the PY files, cross compile to MPY then upload the files to the device. 

# MPY files

During development the plain Python files (*.py) worked ok on the raspberry Pi pico but an doit_esp32_devkit_v1 ran out of memory.
