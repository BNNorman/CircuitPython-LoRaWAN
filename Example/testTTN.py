"""
    testTTN.py
    
    attempts to join TTN (if not previously joined) then sends "Hello World" a number of times. Adheres to the
    regional duty cycle in settings.json AND adheres to the TTN Fair Use Policy (FUP).
    
    Uses NVM to cache TTN MAC settings. NVM can be cleared before or after the code runs if so required.
        
    Downlink messages will logged and printed when received. To send a downlink message you need to setup a downlink message
    using the TTN device console before this code transmits an uplink mnessage.
    
"""
########################################################################
LOG_FILE_NAME="testTTN.log"
JOIN_RETRIES=1
NUM_MESSAGES_TO_SEND=2

CLEAR_NVM_BEFORE=False
CLEAR_NVM_AFTER=False

########################################################################
from microcontroller import nvm

if CLEAR_NVM_BEFORE:
    # The first two bytes indictate the length of the stored information
    nvm[0:2]=bytearray([0,0])
    print("NVM cache cleared before this code run.")

# setup logging - other modules rely on this.
# to reduce code size you would need to remove the logging
# from ALL the modules this testTTN uses.
from LogManager import LogMan
LogMan.setFileStream(LOG_FILE_NAME,"w")    # change to "a" to append
Log=LogMan.getLogger("MAIN",LogMan.NOTSET) # record ALl log messages

# now import other libraries
import sys
import time
from lorawan.LorawanHandler import Handler


# to turn off all except the more severe errors ERROR,WARN,CRITICAL
# try LogMan.ERROR
# must be called AFTER other module imports to allow them to setup
# their loggers
LogMan.setAllLoggerLevels(LogMan.NOTSET) # record ALL log messages


# create the LoRaWAN handler
LW = Handler("settings.json")

DUTY_CYCLE_PERCENT=LW.getDutyCycle() # is based on join frequency
DUTY_WAIT=100-DUTY_CYCLE_PERCENT
        
def downlinkCallback(msg,mtype,fport):
    # downlinks are sent ONLY after an uplink
    # these are not mac commands but either unconfirmed message downklinks or confirmed message downlinks
    # DON'T use confirmed message downlinks as these require the server to send a confirmation
    # which eats into the FUP and daily downlink limit of 10 messages per day
    
    # msg may be a bytearray. adafruit_logging can fall over on those
    log.info(f"Downlink received msg {list(msg)} mtype {mtype} fport {fport}")

def joinTTN(retries):
    """
    joinTTN attempts a number of retries to join TTN
    It is possible that the gateway your uplink used was busy when the TTN server send your JOIN_ACCEPT
    message during RX1 and RX2 receive windows.
    """
    global LW

    while retries>0:
        print("trying to join TTN")
        LW.join() # waits for RX1/RX2 ~ 6 seconds
        if LW.registered():
            return True
        print(f"Retries remaining : {retries-1}")
        retries-=1
    return False

# try to join TTN and send messages (uplinks)

totalAirTime=0

if joinTTN(JOIN_RETRIES):
        
    print("\nJOINED TTN")

    for i in range(0, NUM_MESSAGES_TO_SEND):
        # prepare your message here
        # use LW.sendbytes for binary data
        msg=f"Hello World {i}"
        
        print("Sending {msg}")
        
        Log.info(f"Sending {msg}")
        
        # send transmits then waits for any downlinks
        # returns after RX1+RX2 windows have closed (6 seconds)
        # you can choose which fport the uplink is sent on e.g
        #      LW.send(msg,port)
        # though there is a limit defined by the Lora Alliance
        # the default is fport 1. Stay below fport 200.
        
        if i==NUM_MESSAGES_TO_SEND:
            # no need to wait for DUTY_CYCLE
            break
        
        LW.send(f"Hello World {i}") # send on fport 1
        
        # observe duty cycle limits
        # in reality your messages would be very short and
        # be sent intermittently
        print("Observing legal duty cycle limitation")
        LastAirTime=LW.lastAirTime()
        
        time.sleep(DUTY_WAIT*LW.lastAirTime())

        # TTN FUP is 30s per day
        print("Checking TTN FUP")
        totalAirTime+=LastAirTime
        if totalAirTime>=30:
            print("TTN FUP limit reached")
            break

    Log.info("Finished")
else:
    print("Join failed after {JOIN_RETRIES} retries")


if CLEAR_NVM_AFTER:
    nvm[0:2]=bytearray([0x00,0x00])
    log.info("NVM cleared after this code run")

LogMan.close()
