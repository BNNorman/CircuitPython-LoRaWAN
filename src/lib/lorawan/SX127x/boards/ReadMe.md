# ReadMe.md

Folder names must match board.board_id

For example raspberry_pi_pico 

The folders only contain an __init__.py which has all the necessary code to setup the board pins, LED and SPI.

To add a new MCU create the required folder and copy the existing __init__.py then modify it. Basically change the pins. ESP32 devices pins are often Dnn whereas Pico are GPnn.

NOTE: 	Raspberry Pi Pico does not define the SPI pins so they are obtained from settings.json.
		Other MCUs have board.MOSI etc and so those entries are not required in settings.json.