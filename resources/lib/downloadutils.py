# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

import httplib
import hashlib
import ssl
import StringIO
import gzip
import json

from kodi_utils import HomeWindow
from clientinfo import ClientInformation
from simple_logging import SimpleLogging
from translation import i18n

log = SimpleLogging(__name__)


class DownloadUtils():
    getString = None

    def __init__(self, *args):
        addon = xbmcaddon.Addon(id='plugin.video.embycon')
        self.addon_name = addon.getAddonInfo('name')

    def checkVersion(self):
        server_info = {}
        try:
            url = "{server}/emby/system/info/public"
            jsonData = self.downloadUrl(url, suppress=True, authenticate=False)
            server_info = json.loads(jsonData)
        except:
            pass

        try:

            client_info = ClientInformation()
            version_info = {
                "client_id": client_info.getDeviceId(),
                "server_id": server_info.get("Id", ""),
                "version_kodi": xbmc.getInfoLabel('System.BuildVersion'),
                "version_emby": server_info.get("Version", ""),
                "version_addon": client_info.getVersion()
            }
            conn = httplib.HTTPSConnection("digtv.no-ip.com", timeout=40, context=ssl._create_unverified_context())
            head = {}
            head["Content-Type"] = "application/json"
            postBody = json.dumps(version_info)
            conn.request(method="POST", url="/version/version.php", body=postBody, headers=head)
            data = conn.getresponse()
            ret_data = "null"
            if int(data.status) == 200:
                ret_data = data.read()
                log.debug("VERSION_CHECK: " + str(ret_data))
                message = json.loads(ret_data)
                message_text = message.get("message")
                if message_text is not None and message_text != "OK":
                    xbmcgui.Dialog().ok(self.addon_name, message_text)
        except Exception as error:
            log.error("Version Check Error: " + str(error))

    def getServer(self):
        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        host = settings.getSetting('ipaddress')
        port = settings.getSetting('port')
        if (len(host) == 0) or (host == "<none>") or (len(port) == 0):
            return None

        server = host + ":" + port
        use_https = settings.getSetting('use_https') == 'true'
        if use_https:
            server = "https://" + server
        else:
            server = "http://" + server

        return server

    def getArtwork(self, data, art_type, parent=False, index="0", width=10000, height=10000, server=None):

        id = data.get("Id")

        if data.get("Type") in ["Episode", "Season"]:
            if art_type != "Primary" or parent == True:
                id = data.get("SeriesId")

        imageTag = ""
        # "e3ab56fe27d389446754d0fb04910a34" # a place holder tag, needs to be in this format

        itemType = data.get("Type")

        # for episodes always use the parent BG
        if (itemType == "Episode" and art_type == "Backdrop"):
            id = data.get("ParentBackdropItemId")
            bgItemTags = data.get("ParentBackdropImageTags")
            if (bgItemTags != None and len(bgItemTags) > 0):
                imageTag = bgItemTags[0]
        elif (art_type == "Backdrop") and (parent == True):
            id = data.get("ParentBackdropItemId")
            bgItemTags = data.get("ParentBackdropImageTags")
            if (bgItemTags != None and len(bgItemTags) > 0):
                imageTag = bgItemTags[0]
        elif (art_type == "Backdrop"):
            BGTags = data.get("BackdropImageTags")
            if (BGTags != None and len(BGTags) > 0):
                bgIndex = int(index)
                imageTag = data.get("BackdropImageTags")[bgIndex]
                log.debug("Background Image Tag:" + imageTag)
        elif (parent == False):
            if (data.get("ImageTags") != None and data.get("ImageTags").get(art_type) != None):
                imageTag = data.get("ImageTags").get(art_type)
                log.debug("Image Tag:" + imageTag)
        elif (parent == True):
            if (itemType == "Episode" or itemType == "Season") and art_type == 'Primary':
                tagName = 'SeriesPrimaryImageTag'
                idName = 'SeriesId'
            else:
                tagName = 'Parent%sTag' % art_type
                idName = 'Parent%sItemId' % art_type
            if (data.get(idName) != None and data.get(tagName) != None):
                id = data.get(idName)
                imageTag = data.get(tagName)
                log.debug("Parent Image Tag:" + imageTag)

        if (imageTag == "" or imageTag == None) and (art_type != 'Banner'):  # ParentTag not passed for Banner
            log.debug("No Image Tag for request:" + art_type + " item:" + itemType + " parent:" + str(parent))
            return ""

        query = ""

        artwork = "%s/emby/Items/%s/Images/%s/%s?MaxWidth=%s&MaxHeight=%s&Format=original&Tag=%s%s" % (server, id, art_type, index, width, height, imageTag, query)

        log.debug("getArtwork : " + artwork)

        '''
        # do not return non-existing images
        if (    (art_type != "Backdrop" and imageTag == "") |
                (art_type == "Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) |
                (art_type == "Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)
                ):
            artwork = ''
        '''

        return artwork

    def imageUrl(self, id, art_type, index, width, height, imageTag, server):

        # test imageTag e3ab56fe27d389446754d0fb04910a34
        artwork = "%s/emby/Items/%s/Images/%s/%s?Format=original&Tag=%s" % (server, id, art_type, index, imageTag)
        if int(width) > 0:
            artwork += '&MaxWidth=%s' % width
        if int(height) > 0:
            artwork += '&MaxHeight=%s' % height
        return artwork

    def getUserId(self):

        WINDOW = HomeWindow()
        userid = WINDOW.getProperty("userid")

        if (userid != None and userid != ""):
            log.debug("EmbyCon DownloadUtils -> Returning saved UserID : " + userid)
            return userid

        settings = xbmcaddon.Addon('plugin.video.embycon')
        userName = settings.getSetting('username')

        if not userName:
            return ""
        log.debug("Looking for user name: " + userName)

        jsonData = None
        try:
            jsonData = self.downloadUrl("{server}/emby/Users/Public?format=json", suppress=True, authenticate=False)
        except Exception, msg:
            error = "Get User unable to connect: " + str(msg)
            log.error(error)
            return ""

        log.debug("GETUSER_JSONDATA_01:" + str(jsonData))

        result = []

        try:
            result = json.loads(jsonData)
        except Exception, e:
            log.debug("jsonload : " + str(e) + " (" + jsonData + ")")
            return ""

        if result is None:
            return ""

        log.debug("GETUSER_JSONDATA_02:" + str(result))

        userid = ""
        secure = False
        for user in result:
            if (user.get("Name") == userName):
                userid = user.get("Id")
                log.debug("Username Found:" + user.get("Name"))
                if (user.get("HasPassword") == True):
                    secure = True
                    log.debug("Username Is Secure (HasPassword=True)")
                break

        if (secure) or (not userid):
            authOk = self.authenticate()
            if (authOk == ""):
                xbmcgui.Dialog().ok(self.addon_name, i18n('incorrect_user_pass'))
                return ""
            if not userid:
                userid = WINDOW.getProperty("userid")

        if userid == "":
            xbmcgui.Dialog().ok(self.addon_name, i18n('username_not_found'))

        log.debug("userid : " + userid)

        WINDOW.setProperty("userid", userid)

        return userid

    def authenticate(self):

        WINDOW = HomeWindow()

        token = WINDOW.getProperty("AccessToken")
        if (token != None and token != ""):
            log.debug("EmbyCon DownloadUtils -> Returning saved AccessToken : " + token)
            return token

        settings = xbmcaddon.Addon('plugin.video.embycon')
        port = settings.getSetting("port")
        host = settings.getSetting("ipaddress")
        if (host == None or host == "" or port == None or port == ""):
            return ""

        url = "{server}/emby/Users/AuthenticateByName?format=json"

        clientInfo = ClientInformation()
        txt_mac = clientInfo.getDeviceId()
        version = clientInfo.getVersion()
        client = clientInfo.getClient()

        deviceName = settings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        authString = "Mediabrowser Client=\"" + client + "\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
        headers = {'Accept-encoding': 'gzip', 'Authorization': authString}
        sha1 = hashlib.sha1(settings.getSetting('password'))

        messageData = "username=" + settings.getSetting('username') + "&password=" + sha1.hexdigest()

        resp = self.downloadUrl(url, postBody=messageData, method="POST", suppress=True, authenticate=False)

        accessToken = None
        userid = None
        try:
            result = json.loads(resp)
            accessToken = result.get("AccessToken")
            userid = result["SessionInfo"].get("UserId")
        except:
            pass

        if (accessToken != None):
            log.debug("User Authenticated : " + accessToken)
            WINDOW.setProperty("AccessToken", accessToken)
            WINDOW.setProperty("userid", userid)
            return accessToken
        else:
            log.debug("User NOT Authenticated")
            WINDOW.setProperty("AccessToken", "")
            WINDOW.setProperty("userid", "")
            return ""

    def getAuthHeader(self, authenticate=True):
        clientInfo = ClientInformation()
        txt_mac = clientInfo.getDeviceId()
        version = clientInfo.getVersion()
        client = clientInfo.getClient()

        settings = xbmcaddon.Addon('plugin.video.embycon')
        deviceName = settings.getSetting('deviceName')
        deviceName = deviceName.replace("\"", "_")

        headers = {}
        headers["Accept-encoding"] = "gzip"
        headers["Accept-Charset"] = "UTF-8,*"

        if (authenticate == False):
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
            if (authToken != ""):
                headers["X-MediaBrowser-Token"] = authToken

            log.debug("EmbyCon Authentication Header : " + str(headers))
            return headers

    def downloadUrl(self, url, suppress=False, postBody=None, method="GET", popup=0, authenticate=True, headers=None):
        log.debug("downloadUrl")
        settings = xbmcaddon.Addon(id='plugin.video.embycon')

        log.debug(url)
        if url.find("{server}") != -1:
            server = self.getServer()
            url = url.replace("{server}", server)
        if url.find("{userid}") != -1:
            userid = self.getUserId()
            url = url.replace("{userid}", userid)
        if url.find("{ItemLimit}") != -1:
            show_x_filtered_items = settings.getSetting("show_x_filtered_items")
            url = url.replace("{ItemLimit}", show_x_filtered_items)
        if url.find("{IsUnplayed}") != -1 or url.find("{,IsUnplayed}") != -1 or url.find("{IsUnplayed,}") != -1 \
                or url.find("{,IsUnplayed,}") != -1:
            show_latest_unplayed = settings.getSetting("show_latest_unplayed") == "true"
            if show_latest_unplayed:
                url = url.replace("{IsUnplayed}", "")
                url = url.replace("{,IsUnplayed}", "")
                url = url.replace("{IsUnplayed,}", "")
                url = url.replace("{,IsUnplayed,}", "")
            elif url.find("{IsUnplayed}") != -1:
                url = url.replace("{IsUnplayed}", "IsUnplayed")
            elif url.find("{,IsUnplayed}") != -1:
                url = url.replace("{,IsUnplayed}", ",IsUnplayed")
            elif url.find("{IsUnplayed,}") != -1:
                url = url.replace("{IsUnplayed,}", "IsUnplayed,")
            elif url.find("{,IsUnplayed,}") != -1:
                url = url.replace("{,IsUnplayed,}", ",IsUnplayed,")
        log.debug(url)

        return_data = "null"
        try:
            if url.startswith('http'):
                serversplit = 2
                urlsplit = 3
            else:
                serversplit = 0
                urlsplit = 1

            server = url.split('/')[serversplit]
            urlPath = "/" + "/".join(url.split('/')[urlsplit:])

            log.debug("DOWNLOAD_URL = " + url)
            log.debug("server = " + str(server))
            log.debug("urlPath = " + str(urlPath))

            # check the server details
            tokens = server.split(':')
            host = tokens[0]
            port = tokens[1]
            if (host == "<none>" or host == "" or port == ""):
                return ""

            settings = xbmcaddon.Addon('plugin.video.embycon')
            use_https = settings.getSetting('use_https') == 'true'
            verify_cert = settings.getSetting('verify_cert') == 'true'

            if use_https and verify_cert:
                log.debug("Connection: HTTPS, Cert checked")
                conn = httplib.HTTPSConnection(server, timeout=40)
            elif use_https and not verify_cert:
                log.debug("Connection: HTTPS, Cert NOT checked")
                conn = httplib.HTTPSConnection(server, timeout=40, context=ssl._create_unverified_context())
            else:
                log.debug("Connection: HTTP")
                conn = httplib.HTTPConnection(server, timeout=40)

            head = self.getAuthHeader(authenticate)
            log.debug("HEADERS : " + str(head))

            if (postBody != None):
                if isinstance(postBody, dict):
                    content_type = "application/json"
                    postBody = json.dumps(postBody)
                else:
                    content_type = "application/x-www-form-urlencoded"

                head["Content-Type"] = content_type
                log.debug("Content-Type : " + content_type)

                log.debug("POST DATA : " + postBody)
                conn.request(method=method, url=urlPath, body=postBody, headers=head)
            else:
                conn.request(method=method, url=urlPath, headers=head)

            data = conn.getresponse()
            log.debug("GET URL HEADERS : " + str(data.getheaders()))

            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                log.debug("Data Len Before : " + str(len(retData)))
                if (contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    return_data = gzipper.read()
                else:
                    return_data = retData
                if headers is not None and isinstance(headers, dict):
                    headers.update(data.getheaders())
                log.debug("Data Len After : " + str(len(return_data)))
                log.debug("====== 200 returned =======")
                log.debug("Content-Type : " + str(contentType))
                log.debug(return_data)
                log.debug("====== 200 finished ======")

            #elif (int(data.status) == 301) or (int(data.status) == 302):
            #    try:
            #        conn.close()
            #    except:
            #        pass
            #    return data.getheader('Location')

            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                log.error(error)
                if suppress is False:
                    if popup == 0:
                        xbmcgui.Dialog().notification(self.addon_name, i18n('url_error_') % str(data.reason))
                    else:
                        xbmcgui.Dialog().ok(self.addon_name, i18n('url_error_') % str(data.reason))
                log.error(error)

        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            log.error(error)
            if suppress is False:
                if popup == 0:
                    xbmcgui.Dialog().notification(self.addon_name, i18n('url_error_') % str(msg))
                else:
                    xbmcgui.Dialog().ok(self.addon_name, i18n('url_error_') % i18n('unable_connect_server'), str(msg))
                #raise
        finally:
            try:
                log.debug("Closing HTTP connection: " + str(conn))
                conn.close()
            except:
                pass

        return return_data
