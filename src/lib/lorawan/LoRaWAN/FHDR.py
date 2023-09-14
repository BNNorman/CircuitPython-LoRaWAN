#
# fhdr: devaddr(4) fctrl(1) fcnt(2) fopts(0..N)
#
from .MalformedPacketException import MalformedPacketException
from struct import unpack
from .MHDR import MHDR

class FHDR:

    def read(self, mac_payload):
        if len(mac_payload) < 7:
            raise MalformedPacketException("Invalid fhdr")

        self.devaddr = mac_payload[:4]
        self.fctrl = mac_payload[4]
        self.fcnt = mac_payload[5:7]
        self.fopts = mac_payload[7:7 + (self.fctrl & 0xf)]

    def create(self, mtype, args):
        self.devaddr = [0x00, 0x00, 0x00, 0x00]
        
        # for downlinks fctrl=[ADR:7,RFU:6,ACK:5,FPending:4,FOptsLen:3-0]
        # for uplinks   fctrl=[ADR:7,ADRACKREQ:6,ACK:5,CLASS_B:4,FOptslen:3-0]

        if 'fctrl' in args:
            self.fctrl=args['fctrl']
        else:
            self.fctrl = 0x00


        if 'fcnt' in args:
            fcnt=args['fcnt']
            self.fcnt = [fcnt & 0xFF,fcnt >> 8] # little endian
        else:
            self.fcnt = [0x00, 0x00]
        
        # BNN addition to add any fopts for MAC replies/commands
        if 'fopts' in args:
            self.fopts = args['fopts'] # should this be little endian?
            self.fctrl=self.fctrl | (len(self.fopts) & 0x0F)
        else:
            self.fopts = []
            
        if mtype == MHDR.UNCONF_DATA_UP or mtype == MHDR.UNCONF_DATA_DOWN or\
                mtype == MHDR.CONF_DATA_UP or mtype == MHDR.CONF_DATA_DOWN:
            self.devaddr = list(reversed(args['devaddr']))

    def length(self):
        return 4 + 1 + 2 + (self.fctrl & 0xf)

    def to_raw(self):
        fhdr = []
        fhdr += self.devaddr
        fhdr += [self.fctrl]
        fhdr += self.fcnt
        if self.fopts:
            fhdr += self.fopts
        return fhdr

    def get_devaddr(self):
        return self.devaddr

    def set_devaddr(self, devaddr):
        self.devaddr = devaddr

    def get_fctrl(self):
        return self.fctrl

    def set_fctrl(self, fctrl):
        self.fctrl = fctrl

    def get_fcnt(self):
        return self.fcnt

    def set_fcnt(self, fcnt):
        self.fcnt = fcnt

    def get_fopts(self):
        return self.fopts

    def set_fopts(self, fopts):
        self.fopts = fopts
        # set the FOptsLen 
        self.fctrl=self.fctrl | (len(fopts) & 0x0f) 
