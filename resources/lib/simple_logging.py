# Gnu General Public License - see LICENSE.TXT

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
                xbmc.log(self.format(msg, "ERROR"), level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg, "ERROR").encode('utf-8'), level=xbmc.LOGNOTICE)


    def info(self, msg):
        if(self.level >= 1):
            try:
                xbmc.log(self.format(msg, "INFO"), level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg, "INFO").encode('utf-8'), level=xbmc.LOGNOTICE)

    def debug(self, msg):
        if(self.level >= 2):
            try:
                xbmc.log(self.format(msg, "DEBUG"), level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg, "DEBUG").encode('utf-8'), level=xbmc.LOGNOTICE)

    def format(self, msg, levelValue):
        return self.name + "(" + str(levelValue) + ") -> " + msg