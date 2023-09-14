# Readme.md

copy the contents of the lib folder to your CIRCUITPY\lib folder

If you want to convert the py files to mpy you can get the cross compiler from here:-

https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/mpy-cross/

# lib

adafruit_binascii.mpy
adafruit_logging.mpy
LogManager.py

	adafruit_bus_device
		__init__.py
		i2c_device.mpy
		spi_device.mpy
		
	lorawan
		__init__.py
		Config.py
		LorawanHandler.py
		MAChandler.py
		Strings.py
		
	lorawan\LoRaWAN
		__init__.py
		AES_CMAC.py
		DataPayload.py
		Direction.py
		FHDR.py
		JoinAcceptPayload.py
		JoinRequestPayload.py
		MacPayload.py
		MalformedPacketException.py
		MHDR.py
		PhyPayload.py
	
	
	lorawan\SX127x
		__init__.py
		board_config.py
		constants.py
		LoraArgumentParser.py
		LoraRadio.py


	lorawan\SX127x\boards
		__init__.py
		Readme.md
		
	lorawan\SX127x\boards\raspberry_pi_pico
		__init__.py
	
	
	
	
	