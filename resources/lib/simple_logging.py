
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

    def __str__(self):
        return "LogLevel: " + str(self.level)

    def error(self, msg):
        if(self.level >= 0):
            xbmc.log(self.format(msg))

    def info(self, msg):
        if(self.level >= 1):
            xbmc.log(self.format(msg))

    def debug(self, msg):
        if(self.level >= 2):
            xbmc.log(self.format(msg))

    def format(self, msg):
        return self.name + " -> " + msg