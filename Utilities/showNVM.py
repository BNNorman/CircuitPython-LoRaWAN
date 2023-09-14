"""
showNVM.py

List the contents of the NVM cache

"""
from microcontroller import nvm
import json
import re


cache={}

def loadNvmCache():
    global cache
        
    cacheLen=(nvm[0]<<8)+nvm[1]
        
    if cacheLen==0xffff or cacheLen== 0: # nvm has not been written to
        print("Cache has not been written")
        return
    
    print(f"Reading {cacheLen} bytes")
        
    cacheBytes=nvm[2:cacheLen+2] # convert to json string
    cacheStr=cacheBytes.decode("utf-8")
        
    cache = json.loads(cacheStr)


loadNvmCache()

print("cache contents:-")

for k in sorted(cache.keys()):
    print(k,":",cache[k])


