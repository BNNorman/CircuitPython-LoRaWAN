"""

wipeNVM.py

Resets nvm contents to default (0xff....)
"""

from microcontroller import nvm

nvmLen=len(nvm[0:-1])

nvm[0:nvmLen]=bytearray([0xff]*nvmLen) # zero out the NVM cache

print("NVM has bee reset to the default values")