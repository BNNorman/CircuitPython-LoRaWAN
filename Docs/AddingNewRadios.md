# AddingNewRadios.md

The files which control the radio and MCU are located in the lib/lorawan/SX127x/boards folder.

Folder names must match the CircuitPython board.board_id. For example raspberry_pi_pico etc

The folders only contain an __init__.py which has all the necessary code which. 

1. configures the RFM95 reset pin (RST) for output and sets it high
2. configures the SPI pins and sets NSS high
3. configures the onboard LED and provides a blink() method

To add a new MCU :-

1. create the required folder named using the board_id of your board
2. copy one of the existing __init__.py then modify it.

NOTE: Raspberry Pi Pico does not define the SPI pins so they are obtained from settings.json whereas the ESP32 does 
have board.MOSI etc. 

ESP32 devices - choose a device with PSRAM that is supported here https://circuitpython.org/downloads.
