
# Hardware.md

The code was developed using an RPi Pico with a HopeRF RFM95 transceiver.

My CircuitPython code does not use hardware interruts so the DIO0 and DIO1 signals are unused but if you switch to using LMIC they are required.

![image](https://github.com/BNNorman/CircuitPython-LoRaWAN/assets/15849181/b421ca5a-7f2c-4189-8ae8-b0fefe47fb58)

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


