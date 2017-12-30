# Gnu General Public License - see LICENSE.TXT

import encodings

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
        xbmc.log("LOGGING_ENABLED %s : %s" % (self.name, str(self.enable_logging)), level=xbmc.LOGDEBUG)

    def __str__(self):
        return "LoggingEnabled: " + str(self.enable_logging)

    def error(self, fmt, *args, **kwargs):
        log_line = self.name + " (ERROR) -> " + fmt.format(*args, **kwargs)
        try:
            xbmc.log(log_line, level=xbmc.LOGERROR)
        except UnicodeEncodeError:
            xbmc.log(log_line.encode('utf-8'), level=xbmc.LOGERROR)

    def debug(self, fmt, *args, **kwargs):
        if self.enable_logging:
            log_line = self.name + " (DEBUG) -> " + fmt.format(*args, **kwargs)
            try:
                xbmc.log(log_line, level=xbmc.LOGDEBUG)
            except UnicodeEncodeError:
                xbmc.log(log_line.encode('utf-8'), level=xbmc.LOGDEBUG)
