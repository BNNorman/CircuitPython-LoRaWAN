
# Hardware.md

The code was developed using an RPi Pico with a HopeRF RFM95 transceiver. It has also been tried on a DOIT DEVKIT ESP32 V1.

## RPi Pico

My CircuitPython code does not use hardware interruts so the DIO0 and DIO1 signals are unused but if you switch to using LMIC they are.


### SPI Pins
This scheme keeps all the signals on one side of the RPi Pico and so is more convenient when wiring on a stripboard

| Pico Pin | RFM95 Pin | Comment|
|----------|-----------|--------|
|GP19|MOSI|MOSI|
|GP18|SCK|Clock|
|GP17|NSS|Chip select|
|GP16|MISO|MISO|
|GP22|RES|Reset|
|GP21|DIO1|Not used but if you install LMIC instead it is required|
|GP27|DIO0|Not used but if you install LMIC instead it is required|

## DOIT Devkit ESP32 V1

This device has less available memory than the RPi Pico

### SPI pins

I did not bother with DIO0 or DIO1 here because I was just using the setup to test the CircuitPython LoRaWAN code.

| ESP32 Pin| RFM95 Pin | Comment|
|----------|-----------|--------|
|GPIO23 (VSPI MOSI)|MOSI|MOSI|
|GPIO19|( VSPI MISO)|MISO|MISO|
|GPIO18 (VSPI CLK)|SCK|SPI clock|
|GPIO5 (VSPI CS)|NSS|Chip select|
|GPIO4|RESET|Chip reset|


![image](https://github.com/BNNorman/CircuitPython-LoRaWAN/assets/15849181/ace23d92-17c8-465d-813a-42ceaf3dac07)

