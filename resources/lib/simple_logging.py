# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcaddon
from json_rpc import json_rpc

class SimpleLogging():
    name = ""
    enable_logging = False

    def __init__(self, name):
        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        prefix = settings.getAddonInfo('name')
        self.name = prefix + '.' + name
        params = {"setting": "debug.showloginfo"}
        setting_result = json_rpc('Settings.getSettingValue').execute(params)
        current_value = setting_result.get("result", None)
        if current_value is not None:
            self.enable_logging = current_value.get("value", False)
        #xbmc.log("LOGGING_ENABLED %s: %s" % (self.name, str(self.enable_logging)), level=xbmc.LOGDEBUG)

    def __str__(self):
        return "LoggingEnabled: " + str(self.enable_logging)

    def error(self, msg):
        try:
            xbmc.log(self.format(msg, "ERROR"), level=xbmc.LOGERROR)
        except UnicodeEncodeError:
            xbmc.log(self.format(msg, "ERROR").encode('utf-8'), level=xbmc.LOGERROR)

    def debug(self, msg):
        if (self.enable_logging):
            try:
                xbmc.log(self.format(msg, "DEBUG"), level=xbmc.LOGDEBUG)
            except UnicodeEncodeError:
                xbmc.log(self.format(msg, "DEBUG").encode('utf-8'), level=xbmc.LOGDEBUG)

    def format(self, msg, levelValue):
        return self.name + "(" + str(levelValue) + ") -> " + msg
