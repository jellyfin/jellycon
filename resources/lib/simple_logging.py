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
        new_args = []
        # convert any unicode to utf-8 strings
        for arg in args:
            if isinstance(arg, unicode):
                new_args.append(arg.encode("utf-8"))
            else:
                new_args.append(arg)
        log_line = self.name + " (ERROR) -> " + fmt.format(*new_args)
        xbmc.log(log_line, level=xbmc.LOGDEBUG)

    def debug(self, fmt, *args, **kwargs):
        if self.enable_logging:
            new_args = []
            # convert any unicode to utf-8 strings
            for arg in args:
                if isinstance(arg, unicode):
                    new_args.append(arg.encode("utf-8"))
                else:
                    new_args.append(arg)
            log_line = self.name + " (DEBUG) -> " + fmt.format(*new_args)
            xbmc.log(log_line, level=xbmc.LOGDEBUG)
