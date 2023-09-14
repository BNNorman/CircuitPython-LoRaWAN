#
# frm_payload: appnonce(3) netid(3) devaddr(4) dlsettings(1) rxdelay(1) cflist(0..16)
#
from .MalformedPacketException import MalformedPacketException
from .AES_CMAC import AES_CMAC
import aesio

from LogManager import LogMan
log=LogMan.getLogger("JOIN_ACCEPT") # uses the default log level


class JoinAcceptPayload:

    def read(self, payload):
        if len(payload) < 12:
            raise MalformedPacketException("Invalid join accept payload length");
        self.encrypted_payload = payload

    def create(self, args):
        pass

    def length(self):
        return len(self.encrypted_payload)

    def to_raw(self):
        return self.encrypted_payload

    def to_clear_raw(self):
        """decrypt_payload MUST be called first"""
        log.debug(f" JoinAcceptPayload JOIN ACCEPT to_clear_raw {list(self.payload)}")
        return self.payload

    def get_appnonce(self):
        return self.appnonce

    def get_netid(self):
        return self.netid

    def get_devaddr(self):
        return list(map(int, reversed(self.devaddr)))

    def get_dlsettings(self):
        return self.dlsettings

    def get_rxdelay(self):
        return self.rxdelay

    def get_cflist(self):
        return self.cflist

    def compute_mic(self, key, direction, mhdr):
        mic = []
        mic += [mhdr.to_raw()]
        mic += self.to_clear_raw()

        cmac = AES_CMAC()
        computed_mic = cmac.encode(bytes(key), bytes(mic))[:4]
        log.debug(f"JoinAcceptPayload computed mic was {list(computed_mic)}") # debugging
        return list(map(int, computed_mic))


    """
    The TTN server decrypts messages using AES mode ECB. In order to decrypt
    the message we need to encrypt it. This means the end device only needs to
    know how to encrypt a message
    
    adafruit.aesio ECB mode only works on blocks of 16 bytes so we have to slice
    the message and, if length is not a multiple of 16 add some padding
    
    """
    
    def blockDecryptor(self,appkey,raw_payload):
        """decrypt the payload 16 bytes at a time"""
        
        AES_128 = aesio.AES(bytearray(appkey),aesio.MODE_ECB)
        
        encrypted=raw_payload
        decrypted=bytearray()
        startSlice=0
        while startSlice<len(encrypted):
            L=len(encrypted[startSlice:])
            if  L<16:
                slice=encrypted[startSlice:]+bytearray([0]*(16-L)) # padding, if required
            else:
                slice=encrypted[startSlice:startSlice+16]

            # decrypt the block by encrypting it (see comments above)
            d=bytearray([0]*16)
            AES_128.encrypt_into(bytearray(slice),d)
            decrypted+=d
            
            startSlice=startSlice+16

        return decrypted
    
    def decrypt_payload(self, key, direction, mic):
        
        log.debug(f"decrypt_payload encrypted payload {list(self.encrypted_payload)}")
        
        a = []
        a += self.encrypted_payload
        a += mic
         
        p=self.blockDecryptor(key,a)
        self.payload=p[:-4] # lose the MIC
        
        # frm_payload: appnonce(3) netid(3) devaddr(4) dlsettings(1) rxdelay(1) cflist(0..16)
        # note values are little endian
        self.appnonce = self.payload[:3]
        self.netid = self.payload[3:6]
        self.devaddr = self.payload[6:10]
        self.dlsettings = self.payload[10]
        self.rxdelay = self.payload[11]
        self.cflist = None
        if self.payload[12:]:
            self.cflist = self.payload[12:]

        return list(map(int, self.payload))

    def blockEncryptor(self,appkey,payload):
        """decrypt the payload 16 bytes at a time"""
        
        log.debug(f"JoinAcceptPayload Block encrypting {list(payload)}")
        
        AES_128 = aesio.AES(bytearray(appkey),aesio.MODE_ECB)
        
        encrypted=bytearray()
        payload=bytearray(payload)
        startSlice=0
        while startSlice<len(payload):
            L=len(payload[startSlice:])
            if  L<16:
                slice=payload[startSlice:]+bytearray([0]*(16-L)) # padding, if required
            else:
                slice=payload[startSlice:startSlice+16]

            # decrypt the block by encrypting it (see comments above)
            d=bytearray([0]*16)
            AES_128.encrypt_into(bytearray(slice),d)
            encrypted+=d
            
            startSlice=startSlice+16

        return encrypted
    
    # not certain this is ever called
    def encrypt_payload(self, key, direction, mhdr):
        a = []
        a += self.to_clear_raw()
        a += self.compute_mic(key, direction, mhdr)
        log.info("encrypt_payload() called for JOIN_ACCEPT")
        if len(a)>16:
            log.debug("encrypt_payload trying to encrypt data longer than 16 bytes")
    
        self.encrypted_payload=self.blockEncryptor(key,a)
        return list(map(int, self.encrypted_payload))

    def derive_nwskey(self, key, devnonce):
        log.debug("derive nwskey")
        a = [0x01]
        a += self.get_appnonce()
        a += self.get_netid()
        a += devnonce
        a += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        cipher = aesio.AES(bytes(key),aesio.MODE_ECB)
        e=bytearray([0]*len(a)) # was 16
        cipher.encrypt_into(bytes(a),e)
        return list(map(int, e))

    def derive_appskey(self, key, devnonce):
        log.debug("derive appskey")
        a = [0x02]
        a += self.get_appnonce()
        a += self.get_netid()
        a += devnonce
        a += [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        log.debug(f"derive appskey join accept payload key {key} devnonce {devnonce}")
        cipher = aesio.AES(bytes(key),aesio.MODE_ECB)
        e=bytearray([0]*len(a))
        cipher.encrypt_into(bytes(a),e)
        return list(map(int, e))
