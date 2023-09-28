""" 
board_config.py

Defines the BOARD class to use. Must be imported early.

CircuitPython includes a board.board_id string which identifies the MCU board we are running on.
This script selects the MCU to use.


The MCU modules live in the folder boards/<board.board_id>

Only __init__.py exists and contains the required code for the MCU
 

"""
from LogManager import LogMan
log=LogMan.getLogger("board_config") # use default level

import board

class UnknownBoard(Exception):
    pass

# doing it this way means that only our code can be executed
# and is a security plus.
# Note capitalisation IS IMPORTANT

log.info(f"Configuring for board id={board.board_id}")

# can this be done using variables?
if board.board_id=="raspberry_pi_pico":
    from .boards.raspberry_pi_pico import MCU as BOARD
elif board.board_id=="doit_esp32_devkit_v1":
    from .boards.doit_esp32_devkit_v1 import MCU as BOARD
else:
    log.error(f"{board.board_id} MCU is not configured. Check readme regarding adding new boards.")
    raise UnknownBoard(f"boards/{board.board_id}/__init__.py not found")

"""
now we can do something like this in LorawanHandler.py :-

import board_config as BOARD

config={}

BOARD.setup(config)  # required to setup pins and SPI devices

"""

