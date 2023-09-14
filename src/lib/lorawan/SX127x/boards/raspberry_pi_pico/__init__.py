""" Defines the MCUclass that contains the board pin mappings.

NOTE: DIO pins are not used because the code polls the IRQ register after TX and during RX

"""
import board
from LogManager import LogMan
log=LogMan.getLogger(board.board_id,LogMan.DEBUG)

import time
import digitalio
import busio
from adafruit_bus_device.spi_device import SPIDevice

class MCU():
    """ Board initialisation/teardown and pin configuration is kept here."""
    
    @staticmethod
    def setup(Board):
        """Board is a dict which is the BOARD section from the settings.json"""
        
        log.info(f"Setting up MCU {board.board_id}") 
            
        # all boards should have an LED pin
        MCU.LED = digitalio.DigitalInOut(board.LED)  # depends on the board
        MCU.LED.direction = digitalio.Direction.OUTPUT
        
        # rfm95 reset (optional)
        # RST must be like GP23 otherwise it is ignored
        # we should use an re to match GPnn really
        if "RST" in Board and Board["RST"][:2]=="GP":
            MCU.RST = digitalio.DigitalInOut(getattr(board, Board["RST"]))
            MCU.RST.direction = digitalio.Direction.OUTPUT
        else:
            MCU.RST=None

        # SPI
        try:
            SPI_CLK = getattr(board, Board["SPI_CLK"])
            SPI_CS = getattr(board, Board["SPI_CS"])
            SPI_MOSI = getattr(board, Board["SPI_MOSI"])
            SPI_MISO = getattr(board, Board["SPI_MISO"])
                
            log.info("SPI Pins loaded from settings") 
                
            cs = digitalio.DigitalInOut(SPI_CS)  # Chip Select pin to use
            
            # NOTE spi must exist after setup() exits
            MCU.spi = busio.SPI(SPI_CLK, SPI_MOSI, SPI_MISO)
            MCU.spidev = SPIDevice(MCU.spi, cs, baudrate=Board["SPI_BAUD"], phase=Board["SPI_PHASE"], polarity=Board["SPI_POLARITY"])

            log.info("SPI device setup completed.")

                
        except Exception as e:
            log.error(f"Unable to setup SPI pins Exception: {e}")
            raise
     
        finally:
            # blink 5 times to signal the board is set up
            MCU.blink(.1, 5)
            log.info("MCU Device setup finished")


    @staticmethod
    def led_on(value=1):
        """ Switch the proto shields LED
        :param value: 0/1 for off/on. Default is 1.
        :return: value
        :rtype : int
        """
        MCU.LED.value = 1

        return value

    @staticmethod
    def led_off():
        """ Switch LED off
        :return: 0
        """
        MCU.LED.value = 0
        return 0

    @staticmethod
    def blink(time_sec, n_blink):
        if n_blink == 0:
            return
        MCU.led_on()
        for i in range(n_blink):
            time.sleep(time_sec)
            MCU.led_off()
            time.sleep(time_sec)
            MCU.led_on()
        MCU.led_off()