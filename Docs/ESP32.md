# ESP32.md


I have attempted to use the LoRaWAN code with a DOIT ESP32 Devkit V1. It didn't work because it ran out of memory, even after removing all logging. Interestingly the ESP32 has 520KB of SRAM and the RPi Pico only 264KB yet after installing CircuitPython on the DOIT ESP32 there is less free memory for running programs.

The results of running gc.mem_alloc() and gc.mem_free() on an Rpi Pico and the DOIT ESP32 produces the following information.

|MCU|mem_alloc()|mem_free()|
|---|-----------|----------|
|DOIT ESP32 Devkit V1|1904|11292|
|Raspbery Pi Pico|1904|193296|
|-----|-----|-----|


If you want to use ESP32, presumably because of it's lower sleep power consumption then you need one with PSRAM. Check the CircuitPython downloads page to see which devices are supported.


