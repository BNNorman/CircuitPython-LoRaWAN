"""
Basic interface for an RFM95 LoRa device.
Derived from work by Philip Basford Copyright (C) 2018 to investigate if
CircuitPython was a possible alternative to Python on the Raspberry pi.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

"""
from LogManager import LogMan
log=LogMan.getLogger("LorawanHandler") # uses the default log level
log.debug("Loading")

from random import randrange
import time
import gc
import traceback


from .SX127x.LoRaRadio import LoRa, MODE
from .SX127x.board_config import BOARD
from .SX127x.constants import BW
from .LoRaWAN import new as lorawan_msg
from .LoRaWAN import MalformedPacketException
from .LoRaWAN.MHDR import MHDR
    

from .MAChandler import MAC_commands
from .Config import JsonConfig
from .Strings import *

import traceback

#################################

radioTestCfg=(868.1,9,7) # fixed frequency for testing
TESTING=True

VERBOSE=True

# dio_mappings
txDone_map=[1,0,0,0,0,0]
rxDone_map=[0,0,0,0,0,0]

class radioSettings:
    # used by configureRadio
    JOIN=0
    SEND=1
    RX1=2
    RX2=3
    TEST=4


class TxTimeout(Exception):
    """TX time out"""

class RxTimeout(Exception):
    """RX time out"""

class ClassNotSupported(Exception):
    """Class B operation is not supported"""

class InvalidClass(Exception):
    """Device class is invalid"""

class Handler(LoRa):
    """
        Class to provide a LoRaWAN interface to the RFM95
    """
    
    def __init__(self, config_filename):

        self.confirmWithNextUplink=False # for confirmed data down
        
        log.debug("init starting")
        
        """
            Create the class to interface with the RFM95
        """

        self.JC=JsonConfig(config_filename)                 # load user config
        self.config=self.JC.getConfig()                     # get the config dictionary

        log.debug("Get board config")
        try:
            log.debug("LorawanHandler calling BOARD setup")
            BOARD.setup(self.config["BOARD"])
 
        except Exception as e:
            log.error(f"LorawanHandler Unable to setup the MCU board")
            raise
            
        super().__init__() # LoRaRadio init
        
        log.debug("LoRaRadio has been setup")

        self.MAC=MAC_commands(self.config)    # loads cached MAC info (if any) otherwise config values
        
        self.txDone=False
        self.rxDone=False
        self.dutyCycle=0  # set when selecting a JOIN frequency

        try:
            """
            if config file contains strings where numbers are expected we get an error:-
            
            "...unsupported operand type(s) for <<: 'str' and 'int'"
            
            The RFM9x module is reset by the parent class LoRa found in LoRaRadio.py
            
            """
            self.set_mode(MODE.SLEEP) # includes setting LongRangeMode
            self.set_dio_mapping(txDone_map)
            self.set_sync_word(self.config[TTN][SYNC_WORD])
            self.set_rx_crc(self.config[TTN][RX_CRC])
            self.frequency_plan=self.config[TTN][FREQUENCY_PLAN]
            self.txTimeout=self.config["TX_TIMEOUT"]

           
        except Exception as e:
            time.sleep(2)
            log.error(f"LorawanHandler error initialising radio config {e}. Check config values are not strings")
            raise Exception("lorawanHandler() error initialising LoraRadio")
        
        assert self.get_agc_auto_on() == 1, "AGC auto should be enabled"

        # for downlink DATA messages
        self.downlinkCallback=None
        
        # status
        self.transmitting=False
        self.validMsgRecvd=False     # used to detect valid msg receive in RX1
        
        self.txStart=None            # used to compute last airTime for FUP management
        self.txEnd=None
        
        # if we are a class C device we should be listening unless transmitting
        # but we can only liste if we have joined
        
        if self.registered() and self.getDeviceClass()=="C":
            self.configureRadio(RadioSteetings.RX2)
            self.set_mode(MODE.RXCONT)
            

    def setDownlinkCallback(self,func=None):
        """
        Configure the callback function which will receive
        two parameters: decodedPayload and mtype.

        decodedPayload will be a bytearray. It may be decodable as ascii.
        
        mtype will be MHDR.UNCONF_DATA_DOWN or MHDR.CONF_DATA_DOWN.

        See test_downlink.py for usage.

        func: function to call when a downlink message is received
        """
        if callable(func):
            log.info(f"Setting downlinkCallback to {func}")
            self.downlinkCallback=func
        else:
            log.error(f"downlinkCallback is not callable. Type was {type(func)}")
        
    def configureRadio(self,cfg):
        """
        change radio settings
        
        called whenever there's a change of radio settings
        
        :param cfg: (see radioSettings class)
        """
        freq,sf,bw=0,0,0
        whichCfg="unknown"
        
        if cfg==radioSettings.TEST:
            freq,sf,bw=radioTestCfg
            whichCfg="TEST"
        elif cfg==radioSettings.JOIN:
            # return a randomly selected frequency from the list of join frequencies
            if TESTING:
                freq,sf,bw=radioTestCfg # fixed frequency 
                whichCfg="TEST"
            else:
                freq,sf,bw=self.MAC.getJoinSettings()
                whichCfg="JOIN"
        elif cfg==radioSettings.SEND:
            # return a randomly selected frequency from ALL available channels
            freq,sf,bw=self.MAC.getSendSettings()
            whichCfg="SEND"
        elif cfg==radioSettings.RX1:
            # freq is normally the same as the SEND freq unless a MAC command has changed that
            freq,sf,bw=self.MAC.getRX1Settings()
            whichCfg="RX1"
        elif cfg==radioSettings.RX2:
            freq,sf,bw=self.MAC.getRX2Settings()
            whichCfg="RX2"
        else:
            log.error(f"configureRadio unknown config {cfg}")
            raise Exception(f"Unknown radio config {cfg}")
        
        self.set_pa_config(
            pa_select=1,
            max_power=self.config[TTN][MAX_POWER],
            output_power=self.config[TTN][OUTPUT_POWER]
            )
   
        log.info(f"configureRadio {whichCfg} freq={freq} sf={sf} bw={bw} max power{self.config[TTN][MAX_POWER]} output power {self.config[TTN][OUTPUT_POWER]}")
   
        # now configure the radio
        self.set_mode(MODE.STDBY)
        self.dutyCycle=self.MAC.getMaxDutyCycle(freq)
        self.set_freq(freq) # this will raise a runtime error if freq is invalid or frequency not set
        self.set_spreading_factor(sf)
        self.set_bw(bw)
        
    def getDutyCycle(self):
        """duty cycle is set when frequency is known. I am using one of the JOIN frequencys for that"""
        if self.dutyCycle==0:
            freq,sf,bw=self.MAC.getJoinSettings() # random join frequency
            self.dutyCycle=self.MAC.getMaxDutyCycle(freq)
        return self.dutyCycle
    
    def getDataRate(self):
        """
        returns the current data rate 1..6 which corresponds
        to sf7..sf12 at 125kHz
        """
        return self.MAC.getDataRate()

    def process_JOIN_ACCEPT(self,PhyPayload):
        """
        downlink is a join accept message
        """
        log.debug("process_JOIN_ACCEPT()")

        appkey=self.MAC.getAppKey()
        log.debug(f"appkey {appkey}")
        
        lorawan = lorawan_msg([], appkey) # create the phyPayload object
        lorawan.read(PhyPayload)          # and load the phyPayload into it
                
        decodedPayload=lorawan.get_payload() # calls lorawan.mac_payload.frm_payload.decrypt_payload(self.appkey, self.get_direction(), self.mic)
        
        log.debug(f"decoded_payload {decodedPayload}")
       
        
        try:
            log.debug("Checking MIC")
            lorawan.valid_mic() # throws an exception if MIC not valid
            log.debug("MIC is valid")
        except Exception as e:
            # if decoding failed it probably isn't a valid lorawan packet
            log.error(f"Invalid MIC in JOIN_ACCEPT msg: {e}")
            traceback.print_exception(e)
            return
              
        self.MAC.setLastSNR(self.get_pkt_snr_value()) # used for last status req
        
        # if we receive a valid message in RX1 we don't need
        # to switch to RX2
        self.validMsgRecvd=True
            
        # values from the JOIN_ACCEPT payload
        # spec says payload is
        # join_nonce:3,netId:3;devaddr:4,DL_settings:1,RX_delay:1,cfList:16 (optional)
               
        frm_payload=lorawan.get_mac_payload().get_frm_payload()
        
        log.debug(f"FRM payload {frm_payload}")
            
            
        self.MAC.setRX1Delay(frm_payload.get_rxdelay())
        self.MAC.setDLsettings(frm_payload.get_dlsettings())

            
        # cflist is optional.
        # it defines the 5 additional lora frequencies following the
        # 3 standard join frequencies. 
        # I found this delivers the same frequencies in the config toml
        # lora_freqs[3..7] which came from the TTN frequency plan
        # Un-comment the following lines
        # to use
        # cflist=frm_payload.get_cflist())
        # self.MAC.handleCFlist(cflist)
            
        devaddr=lorawan.get_devaddr()
        nwkskey=lorawan.derive_nwskey(self.devnonce)
        appskey=lorawan.derive_appskey(self.devnonce)
                

        self.MAC.setDevAddr(devaddr)
        self.MAC.setNwkSKey(nwkskey)
        self.MAC.setAppSKey(appskey)

        log.info(f"process_JOIN_ACCEPT: devaddr: {devaddr}")
        log.info(f"process_JOIN_ACCEPT: nwkskey: {nwkskey}")
        log.info(f"process_JOIN_ACCEPT: appskey: {appskey}")
               
        # reset FCntUp after every JOIN
        self.MAC.setFCntUp(1)
                
        # cache any changed MAC values
        self.MAC.saveCache()
            

    def process_DATA_DOWN(self,rawPayload):
        """
        downlink messages can be unconfirmed or confirmed
        
        Optional parts enclosed in [] byte count enclosed in ()
        
        rawPayload=MHDR(1),DEVADDR(4),FCTL(1),FCNT(2),[FOPTS(1..N)],[FPORT(1)],[FRM_PAYLOAD(..N)],MIC(4)
        
        To detect if optional parts exist we need to calc the length.
        
        """
        try:
            log.debug("process_DATA_DOWN")
       
            mtype=rawPayload[0] & 0xF0
            
            # check if just MAC commands
            rawPayloadLen=len(rawPayload)
        
            FOptsLen=rawPayload[5] & 0x0F
        
            # message format - only FRM_PAYLOAD (if any) is encoded in MAC 1.0.x
            # parts enclosed in [] are optional. Size in bytes is enclosed in ()
            # MHDR(1),DEVADDR(4),FCTL(1),FCNT(2),[FOpts(1..N)] [FPort(1)],[FRM_PAYLOAD(1..N)],MIC(4)
            
            msgSize=12 + FOptsLen # excluding FPort & FRM_PAYLOAD
            
            if (rawPayloadLen-msgSize)==0:
                log.info("rawPayload does not have a FRMpayload or FPort - probably just a MAC command")
                self.MAC.processFopts(rawPayload[8:8+FOptsLen])
                return
                    
            # looks like a proper downlink with data sent to me
            # so lets try to understand it
            nwkskey=self.MAC.getNwkSKey()
            appskey=self.MAC.getAppSKey()

            lorawan = lorawan_msg(nwkskey,appskey)
            lorawan.read(rawPayload)
            
            decodedPayload=lorawan.get_payload() # must call before valid_mic()
            
            log.debug(f"Decoded DATA DOWN {decodedPayload}")
            
            lorawan.valid_mic()

            self.validMsgRecvd=True
            
            self.MAC.setLastSNR(self.get_pkt_snr_value()) # used for MAC status reply
                
            if self.downlinkCallback is not None:
                log.debug("Calling downlinkCallback function")
                self.downlinkCallback(decodedPayload,mtype,lorawan.get_mac_payload().get_fport())
             
            # finally process any MAC commands
            log.debug("handle any downlink MAC commands")
            self.MAC.handleCommand(lorawan.get_mac_payload())

            # we may need to ACK
            if mtype==MHDR.CONF_DATA_DOWN:
                self.confirmWithNextUplink=True
              
        except Exception as e:
            log.error(f"Error processing XXX_DATA_DOWN for mtype={mtype} error was {e}.")
            raise
    
    def switchToRX2(self):
        """convenience method """
        log.info(f"switching to RX2 {self.config[TTN][RX2_FREQUENCY]}")
        self.set_mode(MODE.STDBY)
        self.set_freq(self.config[TTN][RX2_FREQUENCY])
        self.set_mode(MODE.RXCONT)
        log.info("RX Window is now RX2")
                    
    def _transmit(self,config,payload):
        """
        send the payload. Listen for downlinks during RX1 and/or RX2 then process any found
        
        :config: will be radioSettings.JOIN or radioSettings.SEND
        :payload: bytearray
        """
        log.debug(f"_transmit payload >{payload}<")
        
        # load the payload into the RFM95 and send it
        self.set_mode(MODE.STDBY)
        self.configureRadio(config)
        self.write_payload(payload)
        self.set_dio_mapping(txDone_map)
        self.txStart=time.monotonic()
        self.set_mode(MODE.TX)
        
        # waiting for tx_done - transmitter will go into STDBY automatically
        # IRQ TxDone flag will be cleared
        # on_tx_done will be called by pollInterruptRegister() which calls on_tx_done()

        txDone=False
        while not txDone:
             txDone=self.get_irq_flags()["tx_done"]
             if (time.monotonic() - self.txStart) > self.config["TX_TIMEOUT"]:
                log.error(f"txDone interrupt not seen within timeout {self.config["TX_TIMEOUT"]}s")
                self.set_mode(MODE.STDBY)
                return
            
        self.txEnd=time.monotonic()    # used (by caller) to calculate transmission time for FUP
        self.clear_irq_flags(TxDone=1) # LoraRadio

        log.info("txDone - switching to RX1")
        
        # https://www.allaboutcircuits.com/textbook/radio-frequency-analysis-design/radio-frequency-demodulation/understanding-i-q-signals-and-quadrature-modulation/
        self.set_invert_iq(1) # invert the LoRa I and Q signals - The Gateway sends downlinks this way to reduce interference
        self.reset_ptr_rx()
        
        #rx windows for switching
        RX1=1
        RX2=2
        
        device_class=self.getDeviceClass()
        
        if device_class not in ["A","C"]:
            log.warning(f"Unsupported device class {device_class} falling back to class A")
            device_class="A"

        # RX1 frequency does not need setting as it is always the same as the TX frequency
        self.set_dio_mapping(rxDone_map)
       
        rx1_timeout = self.MAC.getRX1Delay() + self.config[TTN][RX_WINDOW]
        rx2_timeout = self.MAC.getRX2Delay() + self.config[TTN][RX_WINDOW]

        self.set_mode(MODE.RXCONT)     # LoraRadio is already in MODE.STDBY after transmitting
        rxStart = time.monotonic()
        
        this_rx_window = RX1
        log.info("RX Window is now RX1")
        
        rxDone=False
        while not rxDone:  # can be set in RX1 or RX2 windows
            # do this first as it can call on_rx_done which sets rxDone
            rxDone=self.get_irq_flags()["rx_done"]
             
            if not rxDone and this_rx_window == RX1:
                if (time.monotonic() - rxStart) > rx1_timeout:
                    self.switchToRX2()
                    this_rx_window=RX2
            elif not rxDone and this_rx_window == RX2:
                if (time.monotonic() - rxStart) > rx2_timeout:
                    
                    # class C remains listening in RX2
                    if device_class=="A":
                        log.info("Nothing received during RX1 or RX2")
                        self.set_mode(MODE.SLEEP)
                    return
                                  
        self.clear_irq_flags(RxDone=1) # LoraRadio
        self.processDownlinks()

        # class C remains listening in RX2
        if (this_rx_window!=RX2) and (device_class=="C"):
            self.switchToRX2()
        else:
            self.set_mode(MODE.SLEEP)
        
    def payloadToDecList(self,payload):
        """convenience function for nice log message formatting
        Note adafruit_logging can crash on non-ascii
        """
        out=[]
        for b in payload:
            out.append(b)
        return out
        
        
    def processDownlinks(self):
        """
            handle ANY received data though we should only receive
            a downlink in response to our transmission
        """
        log.debug("Received downlink message...")
  
              
        # read the payload from the radio
        # this may or may not be a valid lorawan message
        rawPayload = self.read_payload(nocheck=True)
        
        log.debug(f"raw payload {self.payloadToDecList(rawPayload)}")
                
        if rawPayload is None:
            log.debug("rawPayload is None")
            return

        # 12 bytes is the absolute minimum rawPayload length
        if len(rawPayload)<12:
            log.debug("received invalid message. Too small.")
            return

              
        # MHDR is not encoded and is first byte of the rawPayload
        mtype=rawPayload[0] & 0xE0
        
        if mtype==MHDR.JOIN_ACCEPT:
            self.process_JOIN_ACCEPT(rawPayload)
            return
                
        # don't process any other messages till we have registered
        # since we don't have the keys to decode FRM payloads that may
        # come from dubious sources
        if not self.registered():
            log.debug(f"received a message mtype={mtype} but we haven't joined yet. Ignored.")
            return
           
        # check the destination devaddr
        
        destAddr=list(rawPayload[1:5])           # devaddr is little endian in the message received
        destAddr.reverse()                       # make it big-endian
        devAddr=list(self.MAC.getDevAddr())      # I store it big-endian so it looks the same as in the TTN console
        
        log.debug(f"Received destAddr {destAddr} my devAddr {devAddr}")
        if destAddr!=devAddr:
            # message is not for me
            log.debug("downlink message is not addressed to me")
            return
               
        # process any other downlink messages
        if mtype==MHDR.UNCONF_DATA_DOWN or mtype==MHDR.CONF_DATA_DOWN:
            self.process_DATA_DOWN(rawPayload)
            return
                
        log.debug(f"Unhandled mtype {mtype}. Message ignored.")        


    def lastAirTime(self):
        """
            return the duration of the last transmission
            enables user to adhere to LoRa Duty Cycle & TTN FUP

        :return: time of last transmission or 0 (none)

        """
        if self.txStart is not None and self.txEnd is not None:
            return self.txEnd-self.txStart
        return 0

        

    def join(self):
        """
        try to join TTN 
        
        The join frequency is randomly chosen from the first three frequencies
        in the frequency plan.

        NOTE: bandwidth (BW) range is defined in dragino/SX127x/constants.py and is essentially 
        an int in range 0..9 determined by the radio not TTN but limited by TTN

        if join fails the caller may retry after a random time period (see LoRaWAN spec)
        
        Here we build the JOIN_REQUEST payload and send it

        """

        log.debug("join() starting")
        
        # have we already joined?
        # this will be true if using ABP
        if self.registered():
            log.debug("Already joined, nothing to do here. Just send data.")
            return

        mode=self.config[TTN][AUTH_MODE]
     
        if mode != AUTH_OTAA:
            log.error(f"Unknown auth_mode {mode}")
            return

        log.debug("Performing OTAA Join")

        
        """
            Perform the OTAA auth in order to get the keys required to transmit
        """
        
        self.devnonce = [randrange(256), randrange(256)] #random devnonce 2 bytes

        appkey=self.MAC.getAppKey()
        appeui=self.MAC.getAppEui()
        deveui=self.MAC.getDevEui()

        log.debug(f"App key = {appkey}")
        log.debug(f"App eui = {appeui}")
        log.debug(f"Dev eui = {deveui}")
        log.debug(f"Devnonce= {self.devnonce}")

        lorawan = lorawan_msg(appkey)
                
        lorawan.create(
                    MHDR.JOIN_REQUEST,
                    {'deveui': deveui, 'appeui': appeui, 'devnonce': self.devnonce})
                
        packet=lorawan.to_raw()
        log.info(f"Join: sending packet {packet} type {type(packet)} size={len(packet)}")
        
        self._transmit(radioSettings.JOIN,packet)
       
    def receive(self):
        """Check if any downlinks have been received in class C operation
            if the device is NOT class C the radio will have been set to sleep after
            the RX1/RX2 windows have closed.
            If a received message contains a frm_payload then the downlinkCallback user function
            will be called. If the message is only MAC commands the caller will be unaware
            of this.
            Users of class C devices need to factor frequent calls to this method in their program loop.
        """
        # sanity chgecks
        if self.getDeviceClass() != "C":
            log.info("Device is not flagged as class C in settings.json")
            return
        
        # after any transmit the device will be left in RXCONT mode
        mode=self.get_mode()
        if mode!=MODE.RXCONT:
            log.info(f"Device is not listening/class C - mode was {mode}")
            return
        
        # ok so we are class C and listening
        # if a message has arrived process it and clear the IRQ flag
        rxDone=self.get_irq_flags()["rx_done"]
        if rxDone:
            self.clear_irq_flags(RxDone=1) # LoraRadio
            self.processDownlinks()
        
    def getDeviceClass(self):
        """convenience function returns the capitalised device class from settings.json"""
        return self.config[TTN][DEVICE_CLASS].upper()
        
            

    def getDutyCycle(self,freq=None):
        """
        returns the maximum duty cycle for the given frequency range
        
        returns None if duty cycle is not in the valid range
        
        :freq: frequency Mhz e.g. 868.1
        :return: duty cycle in range listed in settings.json. Typically 0.1..1.0
        """
        return self.MAC.getMaxDutyCycle(freq)
        
    def registered(self):
        """
            return True if we have a device address.
            
            For ABP this is hard coded but for OTAA it exists only if we have joined.
            
            To force a re-join clear the NVM before restarting.
        """
            
        #log.debug(f"checking if already registered.")
        
        try:

            devaddr=self.MAC.getDevAddr()
                
            #log.debug(f"registered() devaddr {devaddr} len {len(devaddr)}.")
            
            # dev address is always 4 bytes
            if len(devaddr)!=4:
                log.debug("invalid devaddr != 4 bytes")
                return False

            if devaddr==bytearray([0x00, 0x00, 0x00, 0x00]):
                #log.debug("devaddr not assigned ")
                return False
                
            # TTN devaddr always starts 0x26 or 0x27
            if devaddr[0] != 0x26 and devaddr[0] != 0x27:
                log.debug(f"Invalid TTN devaddr {devaddr}, should begin with 0x26 or 0x27")
                return False  
            
            log.info("Already registered")
            return True
                
        except Exception as e:
            log.error(f"whilst checking devaddr {devaddr} error was {e}")
            return False
    
    
    def _sendPacket(self,message,port=1):
        """
        Send the uplink message and any MAC replies

        Used by normal uplink messages. See Join() for actual joining.
        
        We always use a random frequency from the lora_tx_freqs list for sending.
        
        :param message: byte message (not the whole payload, read on)
        :param port: 1..253 is the available range 
        """

        try:
            
            # check if joined
            if not self.registered():
                log.warn("_sendpacket() attempt to send uplink but not joined")
                return
              
            nwkskey=self.MAC.getNwkSKey()
            appskey=self.MAC.getAppSKey()
            lorawan = lorawan_msg(nwkskey,appskey)
            
            
            try:
                FCntUp=self.MAC.getFCntUp()
                if FCntUp is None:
                    FCntUp=0
            except:
                FCntUp=0
            
            devaddr=self.MAC.getDevAddr()
            
            FOpts,FOptsLen=self.MAC.getFOpts() # can be an empty bytearray
            
            # create the LoRaWAN message
            if FOptsLen>0:
                lorawan.create(MHDR.UNCONF_DATA_UP,
                    {
                    'devaddr': devaddr, 
                    'fcnt': FCntUp, 
                    'data': message,
                    'fport':port,
                    'fopts':FOpts
                    })
            else:
                FCtrl=0;
                if self.confirmWithNextUplink:
                    self.confirmWithNextUplink=False
                    FCtrl=0x20 # bit 5 is an ACK
                # we never send confirmed up so the last downlink must have come from the server
                # if someone accidentally set the confirmed checkbox on the V3 messaging
                # panel
                lorawan.create(MHDR.UNCONF_DATA_UP,
                    {
                    'devaddr': devaddr,
                    'fcnt': FCntUp,
                    'data': message,
                    'fport': port,
                    'fctrl': FCtrl
                    })

            self.MAC.setFCntUp(FCntUp+1)
        
            # encode the packet
            payload=lorawan.to_raw()

            # now send it
            self._transmit(radioSettings.SEND,payload)

        except ValueError as err:
            traceback.print_exception(err)
            log.error(f"_sendPacket Value error {err}")

        except Exception as e:
            traceback.print_exception(e)

    def send_bytes(self, message,port=1):
        """
            Send a list of bytes over the LoRaWAN channel

            called by send("message") to create a byte array or directly if message
            is already a byte array
        """
        if self.MAC.getNwkSKey() is None or self.MAC.getAppSKey() is None:
            log.error("no nwkSKey or AppSKey - we need to JOIN first")
            return

        self._sendPacket(message,port)

    def send(self, message, port=1):
        """
            Send a string message over the channel
        """
        #self.send_bytes(list(map(ord, str(message))),port)
        self.send_bytes(message.encode("utf-8"),port)


