from LogManager import LogMan
log=LogMan.getLogger("Config",LogMan.DEBUG)


import json

class JsonConfig:
    """
    provided to read in a json config file and store
    data into a dictionary

    WARNING: Validity of entries in config.toml is not checked

    """
    
    config=None

    def __init__(self,configFile):
        """
        Load the config data from file

        This is never written back to by this program
        """
        
        try:
            with open(configFile,"r") as conf:
                JsonConfig.config=json.loads(conf.read())
                
            #log.info("Config loaded ok")

        except Exception as e:
            raise RuntimeError(f"config load error : {e} - Check the settings file {configFile}")

    def getConfigEntry(self,Entry):
        """
        returns the config dictionary entry

        """
        if Entry in self.config:
            return self.config[Entry]
        else:
            return None
        
    def getConfig(self):
        """
        returns the config dictionary

        Use to simplify access to user settings

        e.g.

        A=JsonConfig("filename")
        Retries=A["TTN"]["join_retries"]

        """
        if self.config is not None:
            return self.config

if __name__ ==  "__main__":
    
    conf=JsonConfig("../setting.json")
