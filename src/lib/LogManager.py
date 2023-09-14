try:
    import adafruit_logging as logging
except:
    raise Exception("adafruit_logging library is required")

# override adafruit_logging format and emit

class StreamHandler(logging.StreamHandler):
    
    def format(self, record: LogRecord) -> str:
        """Generate a timestamped message.

        :param record: The record (message object) to be logged
        """
        return f"{record.created:<0.3f}: {record.name} {record.levelname} - {record.msg}"
    
    def emit(self, record: LogRecord) -> None:
        """Generate the message and write it to the UART.

        :param record: The record (message object) to be logged
        """
        self.stream.write(self.format(record)+self.terminator)
        # with a lot of logging going on this is needed
        # even when LogMan flushes the stream when close() is called
        self.stream.flush()

class LogMan:
    
    stream=None
    streambackup=None
    loggers={}

    # logging levels
    NOTSET=logging.NOTSET
    DEBUG=logging.DEBUG
    INFO=logging.INFO
    WARNING=logging.WARNING
    ERROR=logging.ERROR
    CRITICAL=logging.CRITICAL

    
    @staticmethod
    def setNullHandler():
        if LogMan.streambackup is None:
            LogMan.streambackup=LogMan.stream
        LogMan.stream=logging.NullHandler()
        
    @staticmethod
    def restoreLastHandler():
        if LogMan.streambackup is not None:
            LogMan.stream=logMan.streambackup
            logMan.streambackup=None
        
    @staticmethod
    def setFileStream(filename,mode="a"):
        """Must be called first immediately after importing LogManager and before importing other modules which use LogManager"""
        assert type(filename) is str,"Expected a string for the filename"
        
        try:
            LogMan.stream=open(filename,mode)
            LogMan.handler=StreamHandler(LogMan.stream)
            
        except Exception as e:
            print(f"Unable to create a file stream {e}")
            raise
            
    @staticmethod
    def getLogger(name,level=logging.NOTSET):
        if level is not None:
            assert LogMan.stream is not None,"LogManager stream must be created first with LogMan.setFileStream(<log file name>)"
            assert type(level) is int and level>=0,"getLogger optional level parameter must be an int>=0"
        log=logging.getLogger(name)
        log.addHandler(LogMan.handler)
        log.setLevel(level)
        # save the logger
        LogMan.loggers[name]=log
        return log

    @staticmethod
    def setAllLoggerLevels(newLevel):
        assert type(newLevel) is int
    
        for log in LogMan.loggers:
            LogMan.loggers[log].setLevel(newLevel)
            
        
        
    @staticmethod
    def close():
        LogMan.stream.close() # flushes the stream
