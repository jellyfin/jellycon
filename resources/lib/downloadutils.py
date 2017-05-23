# Gnu General Public License - see LICENSE.TXT

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
from clientinfo import ClientInformation
from simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon." + __name__)

class DownloadUtils():

    getString = None

    def __init__(self, *args):
        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        self.getString = settings.getLocalizedString
        self.addon_name = settings.getAddonInfo('name')

    def getArtwork(self, data, type, parent = False, index = "0", width = 10000, height = 10000, server=None):

        id = data.get("Id")
        '''
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Thumb" and type != "Banner":
                id = data.get("SeriesId")
        '''
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary":
                id = data.get("SeriesId")

        # for episodes and type primary and parent is required then use series ID
        if data.get("Type") == "Episode" and parent == True:
            id = data.get("SeriesId")

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
                log.debug("Background Image Tag:" + imageTag)        
        else:
            if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
                imageTag = data.get("ImageTags").get(type)
                log.debug("Image Tag:" + imageTag)

        #if(imageTag == "" or imageTag == None):
        #    log.debug("No Image Tag for request:" + type + " item:" + itemType + " parent:" + str(parent))
        #    return ""

        query = ""
        
        artwork = "http://%s/emby/Items/%s/Images/%s/%s?MaxWidth=%s&MaxHeight=%s&Format=original&Tag=%s%s" % (server, id, type, index, width, height, imageTag, query)
        
        log.debug("getArtwork : " + artwork)
        
        '''
        # do not return non-existing images
        if (    (type != "Backdrop" and imageTag == "") | 
                (type == "Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) | 
                (type == "Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)                
                ):
            artwork = ''
        '''
        
        return artwork

    def imageUrl(self, id, type, index, width, height, imageTag, server):

        # test imageTag e3ab56fe27d389446754d0fb04910a34
        artwork = "http://%s/emby/Items/%s/Images/%s/%s?MaxWidth=%s&MaxHeight=%s&Format=original&Tag=%s" % (server, id, type, index, width, height, imageTag)
        '''
        artwork = ( "http://" + server + "/emby/Items/" + 
                    str(id) + "/Images/" + type + 
                    "/" + str(index) + 
                    "/" + str(imageTag) + "/original/" + 
                    str(height) + "/" + str(width) + "/0")
        '''
        return artwork
        
    def getUserId(self):

        WINDOW = xbmcgui.Window( 10000 )
        userid = WINDOW.getProperty("userid")

        if(userid != None and userid != ""):
            log.info("EmbyCon DownloadUtils -> Returning saved UserID : " + userid)
            return userid

        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        port = settings.getSetting('port')
        host = settings.getSetting('ipaddress')
        userName = settings.getSetting('username')

        if not userName:
            return ""
        log.info("Looking for user name: " + userName)

        jsonData = None
        try:
            jsonData = self.downloadUrl(host + ":" + port + "/emby/Users/Public?format=json", suppress=True, authenticate=False)
        except Exception, msg:
            error = "Get User unable to connect to " + host + ":" + port + " : " + str(msg)
            log.error(error)
            return ""

        log.info("GETUSER_JSONDATA_01:" + str(jsonData))

        result = []

        try:
            result = json.loads(jsonData)
        except Exception, e:
            log.info("jsonload : " + str(e) + " (" + jsonData + ")")
            return ""           

        log.info("GETUSER_JSONDATA_02:" + str(result))

        userid = ""
        secure = False
        for user in result:
            if(user.get("Name") == userName):
                userid = user.get("Id")
                log.info("Username Found:" + user.get("Name"))
                if(user.get("HasPassword") == True):
                    secure = True
                    log.info("Username Is Secure (HasPassword=True)")
                break

        if (secure) or (not userid):
            authOk = self.authenticate()
            if (authOk == ""):
                return_value = xbmcgui.Dialog().ok(self.getString(30044), self.getString(30044))
                return ""
            if not userid:
                userid = WINDOW.getProperty("userid")

        if userid == "":
            return_value = xbmcgui.Dialog().ok(self.getString(30045),self.getString(30045))

        log.info("userid : " + userid)

        WINDOW.setProperty("userid", userid)

        return userid     
        
    def authenticate(self):
    
        WINDOW = xbmcgui.Window( 10000 )

        token = WINDOW.getProperty("AccessToken")
        if(token != None and token != ""):
            log.info("EmbyCon DownloadUtils -> Returning saved AccessToken : " + token)
            return token

        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        port = settings.getSetting("port")
        host = settings.getSetting("ipaddress")
        if(host == None or host == "" or port == None or port == ""):
            return ""
            
        url = "http://" + host + ":" + port + "/emby/Users/AuthenticateByName?format=json"
    
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getDeviceId()
        version = clientInfo.getVersion()
        client = clientInfo.getClient()

        deviceName = settings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        authString = "Mediabrowser Client=\"" + client + "\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
        headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}    
        sha1 = hashlib.sha1(settings.getSetting('password'))
        
        messageData = "username=" + settings.getSetting('username') + "&password=" + sha1.hexdigest()

        resp = self.downloadUrl(url, postBody=messageData, type="POST", suppress=True, authenticate=False)

        accessToken = None
        userid = None
        try:
            result = json.loads(resp)
            accessToken = result.get("AccessToken")
            userid = result["SessionInfo"].get("UserId")
        except:
            pass

        if(accessToken != None):
            log.info("User Authenticated : " + accessToken)
            WINDOW.setProperty("AccessToken", accessToken)
            WINDOW.setProperty("userid", userid)
            return accessToken
        else:
            log.info("User NOT Authenticated")
            WINDOW.setProperty("AccessToken", "")
            WINDOW.setProperty("userid", "")
            return ""
            
    def getAuthHeader(self, authenticate=True):
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getDeviceId()
        version = clientInfo.getVersion()
        client = clientInfo.getClient()

        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        deviceName = settings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        headers = {}
        headers["Accept-encoding"] = "gzip"
        headers["Accept-Charset"] = "UTF-8,*"
        
        if(authenticate == False):
            authString = "MediaBrowser Client=\"" + client + "\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            headers["Authorization"] = authString
            headers['X-Emby-Authorization'] = authString            
            return headers
        else:
            userid = self.getUserId()
            authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"" + client + "\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            headers["Authorization"] = authString
            headers['X-Emby-Authorization'] = authString        
                
            authToken = self.authenticate()
            if(authToken != ""):
                headers["X-MediaBrowser-Token"] = authToken
            
            log.info("EmbyCon Authentication Header : " + str(headers))
            return headers
    
    def downloadUrl(self, url, suppress=False, postBody=None, type="GET", popup=0, authenticate=True):
        log.info("downloadUrl")
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

            log.info("DOWNLOAD_URL = " + url)
            log.debug("server = "+str(server))
            log.debug("urlPath = "+str(urlPath))
            
            # check the server details
            tokens = server.split(':')
            host = tokens[0]
            port = tokens[1]
            if(host == "<none>" or host == "" or port == ""):
                return ""
            
            conn = httplib.HTTPConnection(server, timeout=40)
            
            head = self.getAuthHeader(authenticate)
            log.info("HEADERS : " + str(head))

            if(postBody != None):
                head["Content-Type"] = "application/x-www-form-urlencoded"
                log.info("POST DATA : " + postBody)
                conn.request(method=type, url=urlPath, body=postBody, headers=head)
            else:
                conn.request(method=type, url=urlPath, headers=head)

            data = conn.getresponse()
            log.debug("GET URL HEADERS : " + str(data.getheaders()))

            contentType = "none"
            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                log.debug("Data Len Before : " + str(len(retData)))
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    link = gzipper.read()
                else:
                    link = retData
                log.debug("Data Len After : " + str(len(link)))
                log.debug("====== 200 returned =======")
                log.debug("Content-Type : " + str(contentType))
                log.debug(link)
                log.debug("====== 200 finished ======")

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                log.error(error)
                if suppress is False:
                    if popup == 0:
                        xbmc.executebuiltin("Notification(%s, %s)" % (self.addon_name, self.getString(30200) % str(data.reason)))
                    else:
                        xbmcgui.Dialog().ok(self.getString(30135),server)
                log.error(error)
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            log.error(error)
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("Notification(%s, %s)" % (self.addon_name, self.getString(30200) % self.getString(30201)))
                else:
                    xbmcgui.Dialog().ok("",self.getString(30204))
                raise
        else:
            try: conn.close()
            except: pass

        return link
