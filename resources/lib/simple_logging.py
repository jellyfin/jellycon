
import xbmc
import xbmcaddon

class SimpleLogging():

    level = 0;
    name = ""

    def __init__(self, name):
        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        log_level = settings.getSetting('logLevel')
        self.level = int(log_level)
        self.name = name

    def getLevel(self):
        return self.level

    def __str__(self):
        return "LogLevel: " + str(self.level)

    def error(self, msg):
        if(self.level >= 0):
            try:
                xbmc.log(self.format(msg))#, level=xbmc.LOGERROR)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg).encode('utf-8'))#, level=xbmc.LOGERROR)


    def info(self, msg):
        if(self.level >= 1):
            try:
                xbmc.log(self.format(msg))#, level=xbmc.LOGINFO)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg).encode('utf-8'))#, level=xbmc.LOGNOTICE)

    def debug(self, msg):
        if(self.level >= 2):
            try:
                xbmc.log(self.format(msg))#, level=xbmc.LOGDEBUG)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg).encode('utf-8'))#, level=xbmc.LOGDEBUG)

    def format(self, msg):
        return self.name + " -> " + msg