# Readme.md

Copy all these files to your CIRCUITPY device (not the lib folder)

boot.py will make your CIRCUITPY drive writeable so that the code can create a log file. However, after copying boot.py to your CIRCUITPY folder and rebooting the device, you will no longer be able to drag and drop files to the CIRCUITPY drive. So, copy ALL the files you need before rebooting.

After a reboot you can still open and edit the files using a program like Thonny.

Before running testTTN.py you need to add your appeui,deveui and appkey values in the OTAA section of settings.json. These keys are MSB first and must be decinmal numbers because JSON does not support hex.

If you are not EU based you will need to modify the TTN section and add your Frequency Plan to settings.json. There is an Australian frequency plan in the AU_Frequency_Plan folder.



