import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import httplib
import hashlib
import StringIO
import gzip
import sys
import json as json
from ClientInformation import ClientInformation

class DownloadUtils():

    logLevel = 0
    addonSettings = None
    getString = None

    def __init__(self, *args):
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
        self.getString = self.addonSettings.getLocalizedString
        level = self.addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)

    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("MBCon DownloadUtils -> " + msg)

    def getArtwork(self, data, type, index = "0", width = 10000, height = 10000):

        id = data.get("Id")
        '''
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Thumb" and type != "Banner":
                id = data.get("SeriesId")
                
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary":
                id = data.get("SeriesId")
        '''
        imageTag = ""
        #"e3ab56fe27d389446754d0fb04910a34" # a place holder tag, needs to be in this format

        itemType = data.get("Type")
        
        # for episodes always use the parent BG
        if(itemType == "Episode" and type == "Backdrop"):
            id = data.get("ParentBackdropItemId")
            bgItemTags = data.get("ParentBackdropImageTags")
            if(bgItemTags != None and len(bgItemTags) > 0):
                imageTag = bgItemTags[0]
        elif(type == "Backdrop"):
            BGTags = data.get("BackdropImageTags")
            if(BGTags != None and len(BGTags) > 0):
                bgIndex = int(index)
                imageTag = data.get("BackdropImageTags")[bgIndex]
                #self.logMsg("Background Image Tag:" + imageTag, level=1)        
        else:
            if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
                imageTag = data.get("ImageTags").get(type)
                #self.logMsg("Image Tag:" + imageTag, level=1)

        if(imageTag == "" or imageTag == None):
            #self.logMsg("No Image Tag", level=1)
            return ""            

        query = ""
        played = "0"

        # use the local image proxy server that is made available by this addons service
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port
        
        artwork = ( "http://" + server + "/mediabrowser/Items/" + str(id) + 
                    "/Images/" + type + 
                    "/" + index + "/" + imageTag + "/original/" + 
                    str(height) + "/" + str(width) + "/" + played + "?" + query)
        
        self.logMsg("getArtwork : " + artwork, level=2)
        
        '''
        # do not return non-existing images
        if (    (type != "Backdrop" and imageTag == "") | 
                (type == "Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) | 
                (type == "Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)                
                ):
            artwork = ''
        '''
        
        return artwork

    def imageUrl(self, id, type, index, width, height, tag):
    
        # CCurlFile::Stat - Failed:
    
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port
        
        # test tag e3ab56fe27d389446754d0fb04910a34
        
        imgeUrl = ( "http://" + server + "/mediabrowser/Items/" + 
                    str(id) + "/Images/" + type + 
                    "/" + str(index) + 
                    "/" + str(tag) + "/original/" + 
                    str(height) + "/" + str(width) + "/0")
        
        return imgeUrl
        
    def getUserId(self):

        WINDOW = xbmcgui.Window( 10000 )
        userid = WINDOW.getProperty("userid")

        if(userid != None and userid != ""):
            xbmc.log("MBCon DownloadUtils -> Returning saved UserID : " + userid)
            return userid
    
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        userName = self.addonSettings.getSetting('username')

        self.logMsg("Looking for user name: " + userName)

        jsonData = None
        try:
            jsonData = self.downloadUrl(host + ":" + port + "/mediabrowser/Users/Public?format=json", authenticate=False)
        except Exception, msg:
            error = "Get User unable to connect to " + host + ":" + port + " : " + str(msg)
            xbmc.log (error)
            return ""

        self.logMsg("GETUSER_JSONDATA_01:" + str(jsonData))

        result = []

        try:
            result = json.loads(jsonData)
        except Exception, e:
            self.logMsg("jsonload : " + str(e) + " (" + jsonData + ")", level=1)
            return ""           

        self.logMsg("GETUSER_JSONDATA_02:" + str(result))

        userid = ""
        secure = False
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")
                self.logMsg("Username Found:" + user.get("Name"))
                if(user.get("HasPassword") == True):
                    secure = True
                    self.logMsg("Username Is Secure (HasPassword=True)")
                break

        if(secure):
            authOk = self.authenticate()
            if(authOk == ""):
                return_value = xbmcgui.Dialog().ok(self.getString(30044), self.getString(30044))
                return ""

        if userid == "":
            return_value = xbmcgui.Dialog().ok(self.getString(30045),self.getString(30045))

        self.logMsg("userid : " + userid)

        WINDOW.setProperty("userid", userid)

        return userid     
        
    def authenticate(self):
    
        WINDOW = xbmcgui.Window( 10000 )

        token = WINDOW.getProperty("AccessToken")
        if(token != None and token != ""):
            xbmc.log("MBCon DownloadUtils -> Returning saved AccessToken : " + token)
            return token
        
        port = self.addonSettings.getSetting("port")
        host = self.addonSettings.getSetting("ipaddress")
        if(host == None or host == "" or port == None or port == ""):
            return ""
            
        url = "http://" + self.addonSettings.getSetting("ipaddress") + ":" + self.addonSettings.getSetting("port") + "/mediabrowser/Users/AuthenticateByName?format=json"
    
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getMachineId()
        version = clientInfo.getVersion()

        deviceName = self.addonSettings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        authString = "Mediabrowser Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
        headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}    
        sha1 = hashlib.sha1(self.addonSettings.getSetting('password'))
        
        messageData = "username=" + self.addonSettings.getSetting('username') + "&password=" + sha1.hexdigest()

        resp = self.downloadUrl(url, postBody=messageData, type="POST", authenticate=False)

        accessToken = None
        try:
            result = json.loads(resp)
            accessToken = result.get("AccessToken")
        except:
            pass

        if(accessToken != None):
            self.logMsg("User Authenticated : " + accessToken)
            WINDOW.setProperty("AccessToken", accessToken)
            return accessToken
        else:
            self.logMsg("User NOT Authenticated")
            WINDOW.setProperty("AccessToken", "")
            return ""
            
    def getAuthHeader(self, authenticate=True):
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getMachineId()
        version = clientInfo.getVersion()
        
        deviceName = self.addonSettings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        if(authenticate == False):
            authString = "MediaBrowser Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            headers = {"Accept-encoding": "gzip", "Accept-Charset" : "UTF-8,*", "Authorization" : authString}        
            return headers
        else:
            userid = self.getUserId()
            authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            headers = {"Accept-encoding": "gzip", "Accept-Charset" : "UTF-8,*", "Authorization" : authString}        
                
            authToken = self.authenticate()
            if(authToken != ""):
                headers["X-MediaBrowser-Token"] = authToken
                    
            xbmc.log("MBCon Authentication Header : " + str(headers))
            return headers
    
    def downloadUrl(self, url, suppress=False, postBody=None, type="GET", popup=0, authenticate=True):
        self.logMsg("== ENTER: getURL ==")
        link = ""
        try:
            if url[0:4] == "http":
                serversplit = 2
                urlsplit = 3
            else:
                serversplit = 0
                urlsplit = 1

            server = url.split('/')[serversplit]
            urlPath = "/"+"/".join(url.split('/')[urlsplit:])

            self.logMsg("DOWNLOAD_URL = " + url)
            self.logMsg("server = "+str(server), level=2)
            self.logMsg("urlPath = "+str(urlPath), level=2)
            
            # check the server details
            tokens = server.split(':')
            host = tokens[0]
            port = tokens[1]
            if(host == "<none>" or host == "" or port == ""):
                return ""
            
            conn = httplib.HTTPConnection(server, timeout=40)
            
            head = self.getAuthHeader(authenticate)
            self.logMsg("HEADERS : " + str(head), level=1)

            if(postBody != None):
                head["Content-Type"] = "application/x-www-form-urlencoded"
                self.logMsg("POST DATA : " + postBody)
                conn.request(method=type, url=urlPath, body=postBody, headers=head)
            else:
                conn.request(method=type, url=urlPath, headers=head)

            data = conn.getresponse()
            self.logMsg("GET URL HEADERS : " + str(data.getheaders()), level=2)

            contentType = "none"
            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                self.logMsg("Data Len Before : " + str(len(retData)), level=2)
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    link = gzipper.read()
                else:
                    link = retData
                self.logMsg("Data Len After : " + str(len(link)), level=2)
                self.logMsg("====== 200 returned =======", level=2)
                self.logMsg("Content-Type : " + str(contentType), level=2)
                self.logMsg(link, level=2)
                self.logMsg("====== 200 finished ======", level=2)

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                xbmc.log(error)
                if suppress is False:
                    if popup == 0:
                        xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                    else:
                        xbmcgui.Dialog().ok(self.getString(30135),server)
                xbmc.log (error)
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            xbmc.log(error)
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(\"MBCon\": URL error: Unable to connect to server,)")
                else:
                    xbmcgui.Dialog().ok("",self.getString(30204))
                raise
        else:
            try: conn.close()
            except: pass

        return link