import sys
import os
import traceback
import hashlib
import time
import xbmcaddon
import xbmc
import urllib
import httplib
import ssl

from clientinfo import ClientInformation
from simple_logging import SimpleLogging

log = SimpleLogging(__name__)

# for info on the metrics that can be sent to Google Analytics
# https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters#events

logEventHistory = {}

# wrap a function to catch, log and then re throw an exception
def log_error(errors=(Exception, )):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except errors as error:
                if not (hasattr(error, 'quiet') and error.quiet):
                    ga = GoogleAnalytics()
                    err_strings = ga.formatException()
                    ga.sendEventData("Exception", err_strings[0], err_strings[1], True)
                log.error(error)
                log.error("log_error: %s \n args: %s \n kwargs: %s" % (func.__name__, args, kwargs))
                raise
        return wrapper
    return decorator

# main GA class
class GoogleAnalytics:

    testing = False
    enabled = True
    
    def __init__(self):

        settings = xbmcaddon.Addon('plugin.video.embycon')
        client_info = ClientInformation()
        self.version = client_info.getVersion()
        self.device_id = client_info.getDeviceId()

        self.enabled = settings.getSetting("metricLogging") == "true"
        
        # user agent string, used for OS and Kodi version identification
        kodi_ver = xbmc.getInfoLabel("System.BuildVersion")
        if not kodi_ver:
            kodi_ver = "na"
        kodi_ver = kodi_ver.strip()
        if kodi_ver.find(" ") > 0:
            kodi_ver = kodi_ver[0:kodi_ver.find(" ")]
        self.userAgent = "Kodi/" + kodi_ver + " (" + self.getUserAgentOS() + ")"
        
        # Use set user name
        self.user_name = settings.getSetting('username') or 'None'
        
        # use md5 for client and user for analytics
        self.device_id = hashlib.md5(self.device_id).hexdigest()
        self.user_name = hashlib.md5(self.user_name).hexdigest()
        
        # resolution
        self.screen_mode = xbmc.getInfoLabel("System.ScreenMode")
        self.screen_height = xbmc.getInfoLabel("System.ScreenHeight")
        self.screen_width = xbmc.getInfoLabel("System.ScreenWidth")

        self.lang = xbmc.getInfoLabel("System.Language")
    
    def getUserAgentOS(self):
    
        if xbmc.getCondVisibility('system.platform.osx'):
            return "Mac OS X"
        elif xbmc.getCondVisibility('system.platform.ios'):
            return "iOS"
        elif xbmc.getCondVisibility('system.platform.windows'):
            return "Windows NT"
        elif xbmc.getCondVisibility('system.platform.android'):
            return "Android"
        elif xbmc.getCondVisibility('system.platform.linux.raspberrypi'):
            return "Linux Rpi"
        elif xbmc.getCondVisibility('system.platform.linux'):
            return "Linux"
        else:
            return "Other"
        
    def formatException(self):

        stack = traceback.extract_stack()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)
        full_tb = stack[:-1] + tb
        #log.error(str(full_tb))

		# get last stack frame
        latestStackFrame = None
        if len(tb) > 0:
            latestStackFrame = tb[-1]
        #log.error(str(tb))

        fileStackTrace = ""
        try:
            # get files from stack
            stackFileList = []
            for frame in full_tb:
                #log.error(str(frame))
                frameFile = (os.path.split(frame[0])[1])[:-3]
                frameLine = frame[1]
                if len(stackFileList) == 0 or stackFileList[-1][0] != frameFile:
                    stackFileList.append([frameFile, [str(frameLine)]])
                else:
                    file = stackFileList[-1][0]
                    lines = stackFileList[-1][1]
                    lines.append(str(frameLine))
                    stackFileList[-1] = [file, lines]
            #log.error(str(stackFileList))

            for item in stackFileList:
                lines = ",".join(item[1])
                fileStackTrace += item[0] + "," + lines + ":"
            #log.error(str(fileStackTrace))
        except Exception as e:
            fileStackTrace = None
            log.error(e)

        errorType = "NA"
        errorFile = "NA"

        if latestStackFrame is not None:
            if fileStackTrace is None:
                fileStackTrace = os.path.split(latestStackFrame[0])[1] + ":" + str(latestStackFrame[1])
            
            codeLine = "NA"
            if(len(latestStackFrame) > 3 and latestStackFrame[3] != None):
                codeLine = latestStackFrame[3].strip()

            errorFile = "%s(%s)(%s)" % (fileStackTrace, exc_obj.message, codeLine)
            errorFile = errorFile[0:499]
            errorType = "%s" % (exc_type.__name__)
            #log.error(errorType + " - " + errorFile)

        del(exc_type, exc_obj, exc_tb)
        
        return errorType, errorFile

    def getBaseData(self):
    
        # all the data we can send to Google Analytics
        data = {}
        data['v'] = '1'
        data['tid'] = 'UA-101964432-1' # tracking id
        
        data['ds'] = 'plugin' # data source
        
        data['an'] = 'EmbyCon' # App Name
        data['aid'] = '1' # App ID
        data['av'] = self.version # App Version
        #data['aiid'] = '1.1' # App installer ID

        data['cid'] = self.device_id # Client ID
        #data['uid'] = self.user_name # User ID

        data['ua'] = self.userAgent # user agent string
        
        # add width and height, only add if full screen
        if self.screen_mode.lower().find("window") == -1:
            data['sr'] = str(self.screen_width) + "x" + str(self.screen_height)
        
        data["ul"] = self.lang
        
        return data
    
    def sendScreenView(self, name):
    
        data = self.getBaseData()
        data['t'] = 'screenview' # action type
        data['cd'] = name
    
        self.sendData(data)
    
    def sendEventData(self, eventCategory, eventAction, eventLabel=None, throttle=False):
        
        # if throttling is enabled then only log the same event every 5 min
        if throttle:
            throttleKey = eventCategory + "-" + eventAction + "-" + str(eventLabel)
            lastLogged = logEventHistory.get(throttleKey)
            if lastLogged != None:
                timeSinceLastLog = time.time() - lastLogged
                if timeSinceLastLog < 300 :
                    log.info("SKIPPING_LOG_EVENT : " + str(timeSinceLastLog) + " " + throttleKey)
                    return
            logEventHistory[throttleKey] = time.time()
        
        data = self.getBaseData()
        data['t'] = 'event' # action type
        data['ec'] = eventCategory # Event Category
        data['ea'] = eventAction # Event Action
        
        if eventLabel is not None :
            data['el'] = eventLabel # Event Label
        
        self.sendData(data)
            
    def sendData(self, data):

        if not self.enabled:
            return

        if self.testing:
            log.info("GA: " + str(data))

        postData = ""
        for key in data:
            postData = postData + key + "=" + urllib.quote(data[key]) + "&"

        server = "www.google-analytics.com:443"
        if self.testing:
            url_path = "/debug/collect"
        else:
            url_path = "/collect"

        ret_data = None
        try:
            conn = httplib.HTTPSConnection(server, timeout=40, context=ssl._create_unverified_context())
            head = {}
            head["Content-Type"] = "application/x-www-form-urlencoded"
            conn.request(method="POST", url=url_path, body=postData, headers=head)
            data = conn.getresponse()
            if int(data.status) == 200:
                ret_data = data.read()
        except Exception as error:
            log.error("Error sending GA data: " + str(error))
        
        if self.testing and ret_data is not None:
            log.info("GA: " + ret_data.encode('utf-8'))
            
    
            