"""
loadNVM.py

Write the contents of NVM from file (NVM.json)

"""
from microcontroller import nvm
import json
import re

NVM={}

def saveToNVM():
        """
        MAC commands received from TTN alter device behaviour the info is cached
        in NVM
        """
        print("Saving MAC cache to NVM")
            
        try:
            cacheStr=json.dumps(NVM)
            cacheLen=len(cacheStr)
            
            cacheBytes=cacheStr.encode("utf-8")
            lenBytes=bytearray([(cacheLen>>8) & 0xff,(cacheLen & 0xff)])
            nvm[0:cacheLen+2]=lenBytes+bytearray(cacheBytes)
            
        except Exception as e:
            print(f"Saving MAC cache to NVM failed {e}.")
            

with open("NVM.json","rt") as f:
    jsonStr=f.read()
    NVM=json.loads(jsonStr)
    saveToNVM()