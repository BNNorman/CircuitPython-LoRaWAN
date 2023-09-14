"""
MAChandler.py

Handles MAC commands sent by the server.

responses are placed in a list of tuples
when the responses are required to add to an uplink
the responses are converted to a bytearray

The array of responses is cleared after reading

All attributes are cached when the class is deleted
and reloaded when it is instantiated.

The initial attributes are set from the config file TTN section
when the class is instantiated and overwritten by the cached values.

To start over, delete the cache file before instantiating this class.

"""

from LogManager import LogMan

log=LogMan.getLogger("MAChandler") # using default level
log.info("Loading")

import json
from .Strings import *
import random
from microcontroller import nvm # used for caching

# MAC commands have requests and answers
# the ID of the command is the same whether it is a REQ or ANS
class MCMD:
    LINK_CHECK_ANS=0x02
    LINK_CHECK_REQ=LINK_CHECK_ANS
    LINK_ADR_REQ=0x03
    DUTY_CYCLE_REQ=0x04
    RX_PARAM_SETUP_REQ=0x05
    DEV_STATUS_REQ= 0x06
    NEW_CHANNEL_REQ=0x07
    RX_TIMING_SETUP_REQ=0x08
    TX_PARAM_SETUP_REQ=0x09
    DL_CHANNEL_REQ=0x0A
    # 0x0B..0x0C RFU
    TIME_ANS=0x0D
    TIME_REQ=TIME_ANS
    # 0x0E..0x0F RFU
    # 0x10..0x1F reserved Class B commands
    # 0x20..0x2F reserved Class C commands
    # 0x30..0x7F RFU
    # 0x80..0xFF proprietry extensions
    """END - allows geany to collapse properly"""


class MAC_commands(object):

    def __init__(self,config): #config is a dict

        assert config is not None, "no config data specified"
            
        log.debug("MAC_Commands init")
        
        self.config=config # dict
            
        self.cache={} # TTN dynamic settings saved in NVM

        # jump table for MAC commands taken from spec 1.0.4
        # REQ are commands from the server requesting some info/changes
        # ANS are in response to MAC commands sent to the server
        self.commands = {
            MCMD.LINK_CHECK_ANS: self.link_check_ans,
            MCMD.LINK_ADR_REQ: self.link_adr_req,
            MCMD.DUTY_CYCLE_REQ: self.duty_cycle_req,
            MCMD.RX_PARAM_SETUP_REQ: self.rx_param_setup_req,
            MCMD.DEV_STATUS_REQ: self.dev_status_req,
            MCMD.NEW_CHANNEL_REQ: self.new_channel_req,
            MCMD.RX_TIMING_SETUP_REQ: self.rx_timing_setup_req,
            MCMD.TX_PARAM_SETUP_REQ: self.tx_param_setup_req,
            MCMD.DL_CHANNEL_REQ: self.dl_channel_req,
            # 0x0B..0x0C RFU
            MCMD.TIME_ANS: self.time_ans,
            # 0x0E..0x0F RFU
            # 0x10..0x1F reserved Class B commands
            # 0x20..0x2F reserved Class C commands
            # 0x30..0x7F RFU
            # 0x80..0xFF proprietry extensions
            }

        self.frequency_plan=self.config[TTN][FREQUENCY_PLAN]
        
        log.info(f"Frequency plan is {self.frequency_plan}")
        
        self.lastSNR=0
        
        self.currentChannel=None  # changes with each transmission

        if not self.loadCache(): # load any cached values
            # initialise values from user config file
            # this gives the code a starting point on first run
            log.info("NVM not set. Using [TTN] section as defaults")
            
        # this will add any missing keys/data pairs but keep
        # current values from loadCache
        self.setCacheDefaults()
        
        try:
            self.saveCache()    # update the NVM cache
        except:
            log.warning("Unable to save cache to NVM. Restart may initiate a rejoin.")
  
                    
        # always reset these
        self.macReplies=bytearray()      # list of replies to MAC commands
        self.macCmds=None                # list of MAC commands in downlink
        self.macIndex=0                  # pointer to next MAC cmd in macCmds

        # the following values are tracked whenever a MAC linkCheckReq command is answered
        #
        # gw_margin is the signal strength above noise floor so min value gives us best
        # indication of decoder success
        # gw_cnt is the number of gateways which received our transmision. the linkCheckReq
        # must be issued a number of times because gateways in reach may not be listening

        self.gw_margin=0        # min is calculated
        self.gw_cnt=255         # max is calculated

    
            
        log.debug("__init__ done")

    def setLastSNR(self,SNR):
        """
        used by status reply to server status req
        
        not cached because it can vary a lot
        """
        log.info(f"last SNR value {SNR}")
        self.lastSNR=SNR

    '''
    getters and setters for cached values
    
    '''

    def getLinkCheckStatus(self):
        return (self.gw_margin,self.gw_cnt)

    def getRX1Delay(self):
        return self.cache[RX1_DELAY]

    def getRX2Delay(self):
        return self.cache[RX2_DELAY]
    
    def setRX1Delay(self,delay):
        """ passed in with JOIN_ACCEPT payload
        
        :param delay: seconds
        :return Nothing: no reply expected 
        """
        log.info(f"set RX1 delay {delay}")
        self.cache[RX1_DELAY]=delay
        self.saveCache()
        
    def getDevAddr(self):
        try:
            return bytearray(self.cache[DEVADDR])
        except:
            return bytearray([0x00,0x00,0x00,0x00])
    
    def setDevAddr(self,DevAddr):
        # DevAddr comes from a downlink and may be a bytearray
        self.cache[DEVADDR]=list(DevAddr)
        self.saveCache()
        
    def getNwkSKey(self):
        return self.cache[NWKSKEY]

    def setNwkSKey(self,key):
        self.cache[NWKSKEY]=key
        self.saveCache()
        
    def getAppSKey(self):
        return self.cache[APPSKEY]

    def setAppSKey(self,appskey):
        self.cache[APPSKEY]=appskey
        self.saveCache()
        
    def getAppKey(self):
        return self.cache[APPKEY]

    def getAppEui(self):
        return self.cache[APPEUI]

    def getDevEui(self):
        return self.cache[DEVEUI]

    def getFCntUp(self):
        return self.cache[FCNTUP]
        
    def setFCntUp(self,count):
        self.cache[FCNTUP]=count
        self.saveCache()

    def getJoinSettings(self):
        """
        When joining only the first three frequencies
        should be used
        
        max duty cycle is also selected
        
        :return (freq,sf,bw)
        """
        self.currentChannel=random.randint(0,len(self.cache[JOIN_FREQS])-1)

        freq=self.cache[JOIN_FREQS][self.currentChannel]

        self.cache[MAX_DUTY_CYCLE]=self.getMaxDutyCycle(freq)
        
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[DATA_RATE]]

        log.debug(f"using join settings: freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw

    def getDataRate(self):
        return self.cache[DATA_RATE]

    def getLastSendSettings(self):
        """
        :return tuple: (freq,sf,bw)
        """
        return self.lastSendSettings
        
    def getSendSettings(self):
        """
        randomly choose a frequency (channel)
        
        once joined all frequencies are available for use
        
        Use current data rate
        
        :return (freq,sf,bw)
        """
        self.currentChannel=random.randint(0,len(self.cache[TX_FREQS])-1)

        freq=self.cache[TX_FREQS][self.currentChannel]
        self.cache[DUTY_CYCLE]=self.getMaxDutyCycle(freq)
          
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[DATA_RATE]]
        
        log.debug(f"using send settings: freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw

    def getRX1Settings(self):
        """
        RX1 frequency varies with frequency plan

        :return (freq,sf,bw)
        """

        # RX1 frequency may have been fixed by MAC command
        if self.cache[RX1_FREQ_FIXED]:
            freq = self.cache[RX1_FREQUENCY]
            log.debug(f"RX1 frequency has been fixed to {freq}")
        else:
            freq = self.cache[RX1_FREQS][self.currentChannel]

        sf, bw = self.config[self.frequency_plan][DATA_RATES][self.cache[RX1_DR]]

        log.debug(f"RX1 settings : freq {freq} sf {sf} bw {bw}")

        return freq, sf, bw

    def getRX2Settings(self):
        """
        RX2 is a fixed frequency,sf and bw
        
        :return (freq,sf,bw)
        """
        freq=self.cache[RX2_FREQUENCY]
        
        sf,bw=self.config[self.frequency_plan][DATA_RATES][self.cache[RX2_DR]]
        
        log.debug(f"rx2 settings freq {freq} sf {sf} bw {bw}")
        return freq,sf,bw
        
    def getMaxDutyCycle(self,freq=None):
        """
        return the max duty cycle for a given frequency
        """
        if (self.currentChannel is None) or (freq is None):
            freq=self.config[self.frequency_plan][TX_FREQS][0] # could use join frequencies
            log.info(f"Nothing has been transmitted yet. Using max duty cycle for {freq} instead")
                
        DC_table=self.config[self.frequency_plan][DUTY_CYCLE_TABLE]
        for (minFreq,maxFreq,dc) in DC_table:
            #self.cache[MAX_EIRP]= eirp
            if minFreq<=freq <=maxFreq:
                return dc
        log.error(f"unable to locate max duty cycle for {freq}. Using 0.1 instead")
        return 0.1

    def getSfBw(self,drIndex):
        """
        gets the data rate for a given data rate index

        returns a tuple (sf,bw)

        The set_bw() function expects a value between 0 and 9

        """

        sf,bw=self.config[self.frequency_plan][DATA_RATES][drIndex]

        return (sf,bw)

    def get_bw_index(self,wanted):
        """

        the set_bw() function takes an index 0-9 check the value is valid

        :param wanted: one of [7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125.0, 250.0, 500.0] kHz

        """
        return self.config[self.frequency_plan][BANDWIDTHS].index(wanted)

    def getFrequencyPlan(self):
        """
        get the frequency plan channel frequencies
        
        used internally
        
        """
        log.info("loading frequency plan")
        try:
            
            log.info(f"Frequency Plan is {self.frequency_plan}")

            self.cache[MAX_CHANNELS]=self.cache.get(MAX_CHANNELS,self.config[self.frequency_plan][MAX_CHANNELS])
            self.channelDRRange = [(0, 7)] * self.cache[MAX_CHANNELS]
            #self.channelFrequencies=self.config[self.frequency_plan][LORA_FREQS]
            self.cache[JOIN_FREQS]=self.cache.get(JOIN_FREQS,self.config[self.frequency_plan][JOIN_FREQS])
            self.cache[TX_FREQS] = self.cache.get(TX_FREQS,self.config[self.frequency_plan][TX_FREQS])
            self.cache[RX1_FREQS] = self.cache.get(RX1_FREQS,self.config[self.frequency_plan][RX1_FREQS])
            self.newChannelIndex=0
            
            log.info("Frequency Plan loaded ok")

        except Exception as e:
            
            log.error(f"error loading frequency plan. Check if it exists in the config toml file. {e}")

    def setDLsettings(self,settings):
        """ 
        passed in with JOIN_ACCEPT payload       
        
        :param settings: upper byte RX1 DR offset, lower RX2 DR
        :return nothing: JOIN_ACCEPT does not expect a reply
        """
        rx1_dr_offset=(settings & 0x70)>>4
      
        dr_table_row=self.config[self.frequency_plan][DR_OFFSET_TABLE][self.cache[DATA_RATE]]
        rx1_dr=dr_table_row[rx1_dr_offset]
        
        self.cache[RX1_DR]=rx1_dr
        self.cache[RX2_DR]=settings & 0x0F
        self.saveCache()
        
        log.info(f"DL settings rx1_dr_offset {rx1_dr_offset} rx1_DR {rx1_dr} rx2_DR {settings & 0x0F}")
        
    def _computeFreq(self,a):
        """
        :param  a: byte array of 3 octets 
        :return f: frequency in xxx.y mHz  format
        """
        freq=(a[2] << 16 ) + (a[1] << 8) + a[0] * 100
        # frequency is like 868100000 but we want 868.1
        return freq/1000000    
        
    def handleCFList(self,delay,cflist):
        """
            upto 16 bytes
            5 channel frequencies in groups of 3 bytes per frequency
            plus one byte 0 passed in with JOIN_ACCEPT payload
        
        :param cflist: 5 channel frequencies packed in 3 bytes LSB first     
        """
        
        log.info("processing cfList from JOIN_ACCEPT")
        
        if cflist[-1:]!=0:
            log.info("cfList type is non-zero")
        
        ch=4;
        for entry in range(5):
            # get each slice
            i=entry*3
            self.lora_freqs[ch]=self._computeFreq(cflist[i:i+3])
            ch+=1
        
    def setCacheDefaults(self):
        """
        default settings
        
        """
        log.info("Setting default MAC cache values using user config values")
        
        self.cache[DATA_RATE]=self.cache.get(DATA_RATE,self.config[TTN][DATA_RATE])
        self.cache[JOIN_FREQS] =self.cache.get(JOIN_FREQS, self.config[self.frequency_plan][JOIN_FREQS])
        self.cache[TX_FREQS] = self.cache.get(TX_FREQS,self.config[self.frequency_plan][TX_FREQS])
        self.cache[RX1_FREQS] = self.cache.get(RX1_FREQS,self.config[self.frequency_plan][RX1_FREQS])
        self.cache[OUTPUT_POWER]=self.cache.get(OUTPUT_POWER,self.config[TTN][OUTPUT_POWER])
        self.cache[MAX_POWER]=self.cache.get(MAX_POWER,self.config[TTN][MAX_POWER])
                
        #self.channelDRrange = [(0,7)] * self.config[self.frequency_plan][MAX_CHANNELS]  # all disabled

        # extract freqs from frequency plan

        self.getFrequencyPlan()

        # the following attributes can be changed by MAC commands
        # not all are cached
        # these are listed in groups according to the MAC command
        # which changes the value
        # they are also over written from the user config and MAC cache
        

        # link ADR req
        # for a in [CH_MASK,CH_MASK_CTL,NB_TRANS]:
        #    self.cache[a]=0

        # Duty Cycle req - percentage airtime allowed
        # duty cycle depends on frequency but is mostly
        # 1% in EU868
        self.cache[DUTY_CYCLE]=self.cache.get(DUTY_CYCLE,self.getMaxDutyCycle())

        # RXParamSetup
        self.cache[RX1_DR]=self.cache.get(RX1_DR,self.config[TTN][RX1_DR])
        self.cache[RX2_DR]=self.cache.get(RX2_DR,self.config[TTN][RX2_DR])

        # TX and RX1 frequencies change, RX2 is constant (in UK)
        # RX1 frequency can be set by MAC
        self.cache[RX1_FREQ_FIXED]=self.cache.get(RX1_FREQ_FIXED,0) # 'False' not supported in JSON
        self.cache[RX2_FREQUENCY]=self.cache.get(RX2_FREQUENCY,self.config[TTN][RX2_FREQUENCY])
        self.cache[RX1_DELAY]=self.cache.get(RX1_DELAY,self.config[TTN][RX1_DELAY])
        self.cache[RX2_DELAY]=self.cache.get(RX2_DELAY,self.config[TTN][RX2_DELAY])
        
        # with OTAA some of these are set after joining
        # and cached so that a JOIN isn't needed every time
        auth_mode=self.config[TTN][AUTH_MODE]
        
        self.cache[APPKEY]=self.cache.get(APPKEY,self.config[TTN][auth_mode][APPKEY])
        self.cache[APPEUI]=self.cache.get(APPEUI,self.config[TTN][auth_mode][APPEUI])
        self.cache[DEVEUI]=self.cache.get(DEVEUI,self.config[TTN][auth_mode][DEVEUI])
                    
        if self.config[TTN][AUTH_MODE]==OTAA:
            # NWKSKEY and APPSKEY are set after joining
            self.cache[DEVADDR]=self.cache.get(DEVADDR,self.config[TTN][auth_mode][DEVADDR])
            self.cache[APPSKEY]=self.cache.get(APPSKEY,[])
            self.cache[NWKSKEY]=self.cache.get(NWKSKEY,[])

        else:
            # ABP settings keys are programmed in settings.json
            self.cache[DEVADDR]=self.cache.get(DEVADDR,self.config[TTN][auth_mode][DEVADDR])
            self.cache[APPSKEY]=self.cache.get(APPSKEY,self.config[TTN][ABP][APPSKEY])
            self.cache[NWKSKEY]=self.cache.get(NWKSKEY,self.config[TTN][ABP][NWKSKEY])

        # frame counts - will be reset on OTAA joining
        self.cache[FCNTUP]=self.cache.get(FCNTUP,self.config[TTN][FCNTUP])
        self.cache[FCNTDN]=self.cache.get(FCNTDN,self.config[TTN][FCNTDN])
             
        log.info("MAC default settings finished")
        
    def loadCache(self):
        """
        load cached mac parameters (if saved)
        
        :return: True if NVM values were loaded, False otherwise
        """
        
        cacheLen=(nvm[0]<<8)+nvm[1]
        
        if cacheLen==0xffff or cacheLen== 0x0000: # nvm has not been written to
            log.info("NVM is empty. Could be first run.")
            return False
        
        log.info("loading cache values from NVM")
        
        cacheBytes=nvm[2:cacheLen+2] # convert to json string
        cacheStr=cacheBytes.decode("utf-8")
        log.debug(f"cacheStr was {cacheStr}")
 
        try:           
            self.cache = json.loads(cacheStr)
    
            log.debug("NVM stored settings loaded to MAC cache ok")
        
        except OSError as e:
            log.error(f"{e}")
           
            
        # do not call saveCache() - loadCache() will do that if
        # the NVM data doesn't exist
        
    def saveCache(self):
        """
        MAC commands received from TTN alter device behaviour the info is cached
        in NVM
        """
        log.info("Saving MAC cache to NVM")
            
        try:
            cacheStr=json.dumps(self.cache)
            cacheLen=len(cacheStr)
            

            cacheBytes=cacheStr.encode("utf-8")
            lenBytes=bytearray([(cacheLen>>8) & 0xff,(cacheLen & 0xff)])
            nvm[0:cacheLen+2]=lenBytes+bytearray(cacheBytes)
            
        except Exception as e:
            log.warning(f"Saving MAC cache to NVM failed {e}.")
            
    def incrementFcntUp(self):
        """
        increments the FcntUp and save to cache
        """
        self.cache[FCNTUP]+=1
        self.saveCache()
        
    def checkFcntDn(self,fcntdn):
        """
        Log a warning if fcntdn is not incrementing

        fcntdn: bytearray, should be incrementing
        """
        
        if type(fcntdn) is bytearray:
            FCntDn=int((fcntdn[0]+256*fcntdn[1]))
        else:
            FCntDn=int(fcntdn) # belt and braces
            
        prev=self.cache[FCNTDN]
        
        if FCntDn<=prev:
            log.warn("received downlink FCntDn < or = previous")
            return
        
        self.cache[FCNTDN]=FCntDn
        self.saveCache()

    def getFOpts(self):
        """
        these are the MAC replies. The spec says the server can send multiple
        commands in a packet.
        
        The replies are cleared when this method is called otherwise
        they would be sent to TTN with every uplink
        
        :param: None
        :return: (Fopts,FoptsLen)
        :rtype: tuple
        """
        FOpts=self.macReplies # should this be reversed?
        FOptsLen=len(FOpts)

        log.info(f"check for FOpts to attach to uplink len={FOptsLen} FOpts={list(FOpts)}")

        self.macReplies=bytearray() # clear them as we don't want to send with every messages

        if FOptsLen==0:
            log.info("no FOpts")
            return [],0
            
        if FOptsLen>0 and FOptsLen<=16:
            return (FOpts,FOptsLen)

        log.warning(f"FOpts len={FOptsLen} exceeds 16 bytes={FOpts}")
        return [],0

####################################################
#
# here are the MAC command handlers
#
# taken from the V1.0.4 spec
#
####################################################

    def handleCommand(self, macPayload):
        """
        these are commands originated from the server

        They are only executed if FPort==0

        MAC conmands are acknowledged by sending an uplink repeating
        the command CID

        This method is called if a message includes a MAC payload
        
        :param macPayload: a MAC payload object
        """
        log.debug("checking MAC payload for MAC commands")


        FCtrl=macPayload.get_fhdr().get_fctrl()
        FOptsLen=FCtrl & 0x0F

        FCnt=macPayload.get_fhdr().get_fcnt() # frame downlink frame counter
        log.debug(f"received frame FCnt={FCnt} expecting > FCntDn={self.cache[FCNTDN]}")
  
        if not type(FCnt) is int:
            # probably a 2 byte list little endian
            FCnt=FCnt[0]+FCnt[1]*256
        self.cache[FCNTDN]=int(FCnt)
    

        # MAC commands can appear in FOpts field or FRMpayload but not both
        # MAC commands appear in FRMpayload if FPort is zero
        FPort=macPayload.get_fport()
        if FPort==0: # MAC commands in Form payload
            FOpts=macPayload.get_frm_payload()
        else:
            FOpts=macPayload.get_fhdr().get_fopts()
    
        self.macReplies=bytearray() # no replies, yet
        
        if len(FOpts)==0:
            # no MAC commands
            log.debug("No FOpts to process")
            return

        self.processFopts(FOpts)

    def processFopts(self,FOpts):
        """
        can be called directly if downlink message does not include a FRM payload
        
        :param FOpts: array of MAC commands
        
        """
        log.info(f"handling downlink FOpts {FOpts}")
        
        self.macIndex=0
        self.macCmds=FOpts
        
        while self.macIndex<len(self.macCmds):
            CID=self.macCmds[self.macIndex]
            # called functions add to self.macReplies
            log.debug(f"Calling MAC cmd with CID {CID}")
            try:
                func = self.commands[CID]
                func()
            except KeyError:
                log.error(f"invalid MAC command CID {CID}. Aborting MAC handling")
                break
                
        # update any changes
        self.saveCache()

    def link_check_req(self):
        """
        adds a link check request to the macReplies list
        this will be sent with the next uplink
        
        The server will send a LINK_CHECK_ANS.
        """
        log.debug("LINK_CHECK_REQ")
        self.macReplies+=bytearray([MCMD.LINK_CHECK_REQ])

    def link_check_ans(self):
        """
        The server sends this to acknowledge us sending a LinkCheckReq
        
        Recieved payload will be 2 bytes [Margin][GwCnt]
        
        GwCnt is number of gateways which received the transmission from us
        Margin is the the demod margin (db) range 0..254 (255 reserved)
        
        no response needed
        """
        log.debug("LINK_CHECK_ANS")
        # values can be retrieved with getLinkCheckStatus()
        self.gw_margin=min(self.gw_margin,self.macCmds[self.macIndex+1])
        self.gw_cnt=max(self.gw_cnt,self.macCmds[self.macIndex+2])
        log.debug(f"link check ans margin {self.gw_margin} GwCnt {self.gw_cnt}")
        self.macIndex+=3
        
    def link_adr_req(self):
        """
        Server is asking us to do a data rate adaption
        payload (bytes) is [DR & txPower:1][chMask:2][redundancy:1]

        ChMask determines the channels usable for uplink access

        data_rate & power [DR: 7..4, Power: 3..0] Region Specific

        redundancy rfu:7, ChMaskCntl:6..4 , NbTrans:3..0

        return status byte: RFU:7..3, PowerAck:2, DRAck: 1, ChMaskAck:0
        """
        log.debug("LINK_ADR_REQ")
        self.cache[RX1_DR]=self.macCmds[self.macIndex+1] & 0xF0 >> 4
        self.cache[OUTPUT_POWER]=self.macCmds[self.macIndex+1] & 0x0F
        self.cache[CH_MASK]=self.macCmds[self.macIndex+2] << 8 & self.macCmds[self.macIndex+3]
        self.cache[CH_MASK_CTL]=self.macCmds[self.macIndex+4] & 0x0e >> 4
        self.cache[NB_TRANS]=self.macCmds[self.macIndex+4] & 0x0F
        self.macReplies+=bytearray([MCMD.LINK_ADR_REQ])
        self.macIndex+=5

    def duty_cycle_req(self):
        """
        Change the duty cycle

        1 byte [RFU: 7..4][MaxDutyCycle: 3..0]

        value not used - we are using the duty_cycle_range in the frequency plan
        section of the config file

        """
        log.debug("DUTY_CYCLE_REQ")
        self.cache[MAX_DUTY_CYCLE]=self.macCmds[self.macIndex+1] & 0x0F
        self.macReplies+=bytearray([MCMD.DUTY_CYCLE_REQ])
        self.macIndex+=2

    def rx_param_setup_req(self):
        """
        Setup RX2 parameters

        payload=[DLSettings:1] [Frequency:3]:
        
        DLsettings [RFU:7,RX1DROffset:6..4,RX2DataRate:3..0]

        reply is 1 byte with bit encoding
        RFU:7..3,RX1DROffsetAck:2, RX2DataRateACK:2,ChannelACK:0
        """
        log.debug("RX_PARAM_SETUP_REQ")

        DLSettings=self.macCmds[self.macIndex+1]

        # TODO only if all are valid otherwise no change
        reply=0x00
        
        rx1_dr_offset=(DLSettings & 0xE0) >> 4
        if 0<=rx1_dr_offset<=5:
            reply=reply or 0x01
            
        rx2_dr_index=(DLSettings & 0x0F)
        if 0<=rx2_dr_index<=8:
            reply=reply or 0x02
            
        freq=self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+4])
        
        if freq in self.cache[RX1_FREQS][self.currentChannel]:
            reply=reply or 0x04
            
        if reply==0x07:
            self.cache[RX1_DR]+=rx1_dr_offset
            self.cache[RX2_DR]=rx2_dr_index
            self.cache[RX2_FREQUENCY]=freq
        
        # Channel ACK       0=unusable, 1 ok
        # RX2DataRateAck    0=unknown data rate, 1 ok
        # RX1DROffsetACK    0=not in allowed ranbge, 1 ok
        self.macReplies+=bytearray([MCMD.RX_PARAM_SETUP_REQ,0x07])
        self.macIndex+=5

    def dev_status_req(self):
        """
        Server is asking for device status

        return 2 bytes [battery][RadioStatus]

        Battery
        0 = connected to external power source
        1..254 battery level
        255 - not able to measure

        Radio Status from last dev_status_req command
        bits 5..0 SNR 6 bit signed int

        """
        log.info(f"DEV_STATUS_REQ - returns (0,{int(self.lastSNR)})")
        self.macReplies+=bytearray([MCMD.DEV_STATUS_REQ,0,int(self.lastSNR)])
        self.macIndex+=1

    def new_channel_req(self):
        """
        modify a channel

        payload [ChIndex:0][Frequency:1..3][DRRange:4]

        TODO split DRRange

        reply 1 byte encoded RFU:7..2, DataRateOk: 1, ChannelFreqOk 0
        """
        log.debug("NEW_CHANNEL_REQ")

        chIndex = self.macCmds[self.macIndex+1]
        newFreq=self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+5])
        
        DRRange = self.macCmds[self.macIndex+5] # uplink data rate range (max,min)
        
        maxDR=(DRRange &0xF0) >>4
        minDR=(DRRange &0x0F)
        
        # TODO - check newFreq is possible first
        # needs to know region parameters
        minFreq=min(self.cache[TX_FREQS])
        maxFreq=max(self.cache[TX_FREQS])

        if not (minFreq<=newFreq<=maxFreq):
            log.info(f"new freq {newFreq} not in range min {minFreq} - {maxFreq}")
            self.macReplies+=bytearray([MCMD.NEW_CHANNEL_REQ,0x02])
  
        else:
            self.cache[TX_FREQS][chIndex]=newFreq
            self.channelDRRange[chIndex] = (minDR,maxDR)
            
            log.info(f"NewChannelReq chIndex {chIndex} freq {newFreq} maxDR {maxDR} minDR {minDR}")

            # answer - assume all ok
            self.macReplies+=bytearray([MCMD.NEW_CHANNEL_REQ,0x03])
        
        self.macIndex+=6

    def rx_timing_setup_req(self):
        """
        payload is 1 byte RX1 delay encoded in bits3..0
        """
        log.debug("RX_TIMING_SETUP_REQ")

        rx1_delay=self.macCmds[self.macIndex+1] & 0x0f # seconds
        if rx1_delay == 0:
            rx1_delay = 1
            
        self.cache[RX1_DELAY]=rx1_delay

        log.info(f"rx timing setup RX1 delay={rx1_delay}")
        
        self.macReplies+=bytearray([MCMD.RX_TIMING_SETUP_REQ])
        self.macIndex+=2

    def tx_param_setup_req(self, mac_payload):
        """
        payload 1 byte
        [RFU:7..6][DownlinkDwellTime:5][UplinkDwellTime:4][maxEIRP:3..0]

        DwellTimes: 0= no limit, 1=400ms
        
        Currently the values are stored and acknowledged but not used
        """
        log.debug("TX_PARAM_SETUP_REQ")
        dldt=self.macCmds[self.macIndex+1] & 0x20 >> 5
        uldt=self.macCmds[self.macIndex+1] & 0x10 >> 4
        maxEirp=self.macCmds[self.macIndex+1] & 0x0F
        
        self.cache[DOWNLINK_DWELL_TIME]=dldt
        self.cache[UPLINK_DWELL_TIME]=uldt
        self.cache[MAX_EIRP]=maxEirp
        
        log.info(f"tx param setup DL dwell {dldt} UL dwell {uldt} maxEIRP {maxEirp}")
        
        self.macReplies+=bytearray([MCMD.TX_PARAM_SETUP_REQ])
        self.macIndex += 2

    def dl_channel_req(self):
        """
        only EU863-870 & CN779-787

        payload 4 bytes
        [ChIndex:1][Freq:3]

        reply 1 byte bit encoded
        [RFU 7:2][Uplink Freq Exists 1][channel freq ok 0]

        """
        log.debug("DL_CHANNEL_REQ")
        chIndex = self.macCmds[self.macIndex+1]
        newFreq =self._computeFreq(self.macCmds[self.macIndex+2:self.macIndex+5])
        #self.channelFrequencies[ChIndex] = newFreq
        self.cache[RX1_FREQS][chIndex]=newFreq
        self.cache[RX1_FREQ_FIXED]=True
        self.cache[RX1_FREQUENCY]=newFreq

        log.info(f"DL channel req ChIndex {chIndex} newFreq {newFreq}")

        # answer - 
        # assume Uplink Frequency exists and channel freq ok
        self.macReplies+=bytearray([MCMD.DL_CHANNEL_REQ,0x03])
        self.macIndex += 5

    def time_req(self):
        """
        prompt the server for a TIME_ANS
        """
        log.debug("TIME_REQ")
        self.macReplies+=bytearray([MCMD.TIME_REQ])

    def time_ans(self):
        """
        introduced in 1.0.3

        It is the time at the end of the uplink transmission requesting it.

        payload 5 bytes
        [seconds since epoch:0..3][fractional seconds:4]

        Fractional seconds are 1/256 s increments

        Received as a Class A downlink

        """
        log.debug("TIME_ANS")
        seconds=self.macCmds[self.macIndex+1:self.macIndex+5]
        fraction=self.macCmds[self.macIndex+5] / 256


        log.info(f"server time was {seconds}.{fraction}")

        # to use this the caller needs to track time of sending
        # warning, using the returned values can be a problem
        # we can determin the time the server received the request
        # but it will be hard to tell how long it takes to receive
        # the information back hence there will be an error. However,
        # if the end device time is massively different then it should be 
        # corrected but the Dragino HAT has a GPS and can be time synced to that
        # use the server time at your peril

        # this is a response from the server when we send a time_req.
        # Does not require an ACK
        self.macIndex+=6
