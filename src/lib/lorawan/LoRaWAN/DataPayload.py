#
# frm_payload: data(0..N)
#
from .AES_CMAC import AES_CMAC
import aesio
import math

from LogManager import LogMan
log=LogMan.getLogger("DataPayload") # uses the default log level


class DataPayload:

    def read(self, mac_payload, payload):
        log.debug(f"DataPayload.read() payload {payload}")
        self.mac_payload = mac_payload
        self.payload = payload

    def create(self, mac_payload, key, args):
        self.mac_payload = mac_payload
        self.set_payload(key, 0x00, args['data'])

    def length(self):
        return len(self.payload)

    def to_raw(self):
        return self.payload

    def set_payload(self, key, direction, data):
        self.payload = self.encrypt_payload(key, direction, data)

    def compute_mic(self, key, direction, mhdr):
        mic = [0x49]
        mic += [0x00, 0x00, 0x00, 0x00]
        mic += [direction]
        mic += self.mac_payload.get_fhdr().get_devaddr()
        mic += self.mac_payload.get_fhdr().get_fcnt()
        mic += [0x00]
        mic += [0x00]
        mic += [0x00]
        mic += [1 + self.mac_payload.length()]
        mic += [mhdr.to_raw()]
        mic += self.mac_payload.to_raw()

        cmac = AES_CMAC()
        computed_mic = cmac.encode(bytes(key), bytes(mic))[:4]
        return list(map(int, computed_mic))

    def decrypt_payload(self, key, direction, mic):
        """TTN uses decryption so we only use encryption"""
        log.debug(f"decrypt_payload key {key}")
        k = int(math.ceil(len(self.payload) / 16.0))

        a = []
        for i in range(k):
            a += [0x01]
            a += [0x00, 0x00, 0x00, 0x00]
            a += [direction]
            a += self.mac_payload.get_fhdr().get_devaddr()
            a += self.mac_payload.get_fhdr().get_fcnt()
            a += [0x00] # fcnt 32bit
            a += [0x00] # fcnt 32bit
            a += [0x00]
            a += [i+1]

        cipher = aesio.AES(bytes(key),aesio.MODE_ECB)
        s=bytearray([0]*len(a))
        cipher.encrypt_into(bytes(a),s)

        padded_payload = bytearray([0]*16)
        padding=bytearray([0x00] * 16)
        
        if type(self.payload) is list:
            payload=bytearray(self.payload)
        else:
            payload=self.payload
        
        
        for i in range(k):
            idx = (i + 1) * 16
            padded_payload += (payload[idx - 16:idx] + padding)[:16]

        payload = []
        for i in range(len(self.payload)):
            payload += [s[i] ^ padded_payload[i]]
        return list(map(int, payload))

         
    def encrypt_payload(self, key, direction, data):
        log.debug(f"encrypt_payload data {data} key {key}")
        k = int(math.ceil(len(data) / 16.0))

        a = []
        for i in range(k):
            a += [0x01]
            a += [0x00, 0x00, 0x00, 0x00]
            a += [direction]
            a += self.mac_payload.get_fhdr().get_devaddr()
            a += self.mac_payload.get_fhdr().get_fcnt()
            a += [0x00] # fcnt 32bit
            a += [0x00] # fcnt 32bit
            a += [0x00]
            a += [i+1]
            
        cipher = aesio.AES(bytes(key),aesio.MODE_ECB)
        
        s=bytearray([0]*len(a))
        cipher.encrypt_into(bytearray(a),s)
        
        data=bytearray(data)

        padded_payload = bytearray()
        padding=bytearray([0x00]*16)
        for i in range(k):
            idx = (i + 1) * 16
            padded_payload += (data[idx - 16:idx] + padding)[:16]

        log.debug(f"data={data} padded payload {padded_payload}")
        
        payload = []
        for i in range(len(data)):
            payload += [s[i] ^ padded_payload[i]]
            
        log.debug(f"encrypt_payload returns {payload}")
        return list(map(int, payload))
