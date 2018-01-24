# Gnu General Public License - see LICENSE.TXT
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import re
import encodings
import string
import random
import urllib
import json
import httplib
import base64
import sys
import binascii

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from clientinfo import ClientInformation
from json_rpc import json_rpc
from translation import i18n
from datamanager import DataManager

# define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, media_source, force_transcode, play_session_id):
        log.debug("getPlayUrl")
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        playback_type = addonSettings.getSetting("playback_type")
        server = downloadUtils.getServer()
        log.debug("playback_type: {0}", playback_type)
        if force_transcode:
            log.debug("playback_type: FORCED_TRANSCODE")
        playurl = None
        log.debug("play_session_id: {0}", play_session_id)
        media_source_id = media_source.get("Id")
        log.debug("media_source_id: {0}", media_source_id)

        is_h265 = False
        streams = media_source.get("MediaStreams", [])
        for stream in streams:
            if stream.get("Type", "") == "Video" and stream.get("Codec", "") in ["hevc", "h265"]:
                is_h265 = True
                break
        if is_h265:
            log.debug("H265_IS_TRUE")
            h265_action = addonSettings.getSetting("h265_action")
            if h265_action == "1":
                log.debug("H265 override play action: setting to Direct Streaming")
                playback_type = "1"
            elif h265_action == "2":
                log.debug("H265 override play action: setting to Transcode Streaming")
                playback_type = "2"

        if force_transcode:
            playback_type = "2"

        # transcode
        if playback_type == "2":

            playback_bitrate = addonSettings.getSetting("playback_bitrate")
            log.debug("playback_bitrate: {0}", playback_bitrate)

            playback_max_width = addonSettings.getSetting("playback_max_width")
            playback_video_force_8 = addonSettings.getSetting("playback_video_force_8") == "true"

            clientInfo = ClientInformation()
            deviceId = clientInfo.getDeviceId()
            bitrate = int(playback_bitrate) * 1000
            user_token = downloadUtils.authenticate()

            playurl = ("%s/emby/Videos/%s/master.m3u8" +
                       "?MediaSourceId=%s" +
                       "&PlaySessionId=%s" +
                       "&VideoCodec=h264" +
                       "&AudioCodec=ac3" +
                       "&MaxAudioChannels=6" +
                       "&deviceId=%s" +
                       "&VideoBitrate=%s" +
                       "&maxWidth=%s")
            playurl = playurl % (server, id, media_source_id, play_session_id, deviceId, bitrate, playback_max_width)
            if playback_video_force_8:
                playurl = playurl + "&MaxVideoBitDepth=8"
            playurl = playurl + "&api_key=" + user_token

        # do direct path playback
        elif playback_type == "0":
            playurl = media_source.get("Path")

            # handle DVD structure
            if (media_source.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
            elif (media_source.get("VideoType") == "BluRay"):
                playurl = playurl + "/BDMV/index.bdmv"

            smb_username = addonSettings.getSetting('smbusername')
            smb_password = addonSettings.getSetting('smbpassword')

            # add smb creds
            if smb_username == '':
                playurl = playurl.replace("\\\\", "smb://")
            else:
                playurl = playurl.replace("\\\\", "smb://" + smb_username + ':' + smb_password + '@')

            playurl = playurl.replace("\\", "/")

        # do direct http streaming playback
        elif playback_type == "1":
            playurl = ("%s/emby/Videos/%s/stream" +
                       "?static=true" +
                       "&PlaySessionId=%s" +
                       "&MediaSourceId=%s")
            playurl = playurl % (server, id, play_session_id, media_source_id)
            user_token = downloadUtils.authenticate()
            playurl = playurl + "&api_key=" + user_token

        log.debug("Playback URL: {0}", playurl)
        return playurl, playback_type

    def getStrmDetails(self, media_source):
        playurl = None
        listitem_props = []

        contents = media_source.get('Path').encode('utf-8')  # contains contents of strm file with linebreaks

        line_break = '\r'
        if '\r\n' in contents:
            line_break = '\r\n'
        elif '\n' in contents:
            line_break = '\n'

        lines = contents.split(line_break)
        for line in lines:
            line = line.strip()
            log.debug("STRM Line: {0}", line)
            if line.startswith('#KODIPROP:'):
                match = re.search('#KODIPROP:(?P<item_property>[^=]+?)=(?P<property_value>.+)', line)
                if match:
                    item_property = match.group('item_property')
                    property_value = match.group('property_value')
                    log.debug("STRM property found: {0} value: {1}", item_property, property_value)
                    listitem_props.append((item_property, property_value))
                else:
                    log.debug("STRM #KODIPROP incorrect format")
            elif line.startswith('#'):
                #  unrecognized, treat as comment
                log.debug("STRM unrecognized line identifier, ignored")
            elif line != '':
                playurl = line
                log.debug("STRM playback url found")

        log.debug("Playback URL: {0} ListItem Properties: {1}", playurl, listitem_props)
        return playurl, listitem_props


def getDetailsString():

    addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
    include_media = addonSettings.getSetting("include_media") == "true"
    include_people = addonSettings.getSetting("include_people") == "true"
    include_overview = addonSettings.getSetting("include_overview") == "true"

    detailsString = "DateCreated,EpisodeCount,SeasonCount,Path,Genres,Studios,Etag"

    if include_media:
        detailsString += ",MediaStreams"

    if include_people:
        detailsString += ",People"

    if include_overview:
        detailsString += ",Overview"

    return detailsString


def getChecksum(item):
    userdata = item['UserData']
    checksum = "%s_%s_%s_%s_%s_%s_%s" % (
        item['Etag'],
        userdata['Played'],
        userdata['IsFavorite'],
        userdata.get('Likes', "-"),
        userdata['PlaybackPositionTicks'],
        userdata.get('UnplayedItemCount', "-"),
        userdata.get("PlayedPercentage", "-")
    )

    return checksum


def getArt(item, server, widget=False):
    art = {
        'thumb': '',
        'fanart': '',
        'poster': '',
        'banner': '',
        'clearlogo': '',
        'clearart': '',
        'discart': '',
        'landscape': '',
        'tvshow.fanart': '',
        'tvshow.poster': '',
        'tvshow.clearart': '',
        'tvshow.clearlogo': '',
        'tvshow.banner': '',
        'tvshow.landscape': ''
    }
    item_id = item["Id"]

    image_id = item_id
    imageTags = item["ImageTags"]
    if imageTags is not None and imageTags["Primary"] is not None:
        image_tag = imageTags["Primary"]
        if widget:
            art['thumb'] = downloadUtils.imageUrl(image_id, "Primary", 0, 400, 400, image_tag, server=server)
        else:
            art['thumb'] = downloadUtils.getArtwork(item, "Primary", server=server)

    item_type = item["Type"]

    if item_type == "Episode" or item_type == "Season":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=True, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['tvshow.fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)
    elif item_type == "Series":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Art", parent=False, server=server)
        art['tvshow.clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=False, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=False, server=server)

    if item_type == "Episode":
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
    else:
        art['poster'] = art['thumb']

    art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", server=server)
    if not art['fanart']:
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)

    if not art['landscape']:
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", server=server)
        if not art['landscape']:
            art['landscape'] = art['fanart']

    if not art['thumb']:
        art['thumb'] = art['landscape']

    art['banner'] = downloadUtils.getArtwork(item, "Banner", server=server)
    art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", server=server)
    art['clearart'] = downloadUtils.getArtwork(item, "Art", server=server)
    art['discart'] = downloadUtils.getArtwork(item, "Disc", server=server)

    return art


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def cache_artwork():
    log.debug("cache_artwork")

    xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    # is the web server enabled
    web_query = {"setting": "services.webserver"}
    result = json_rpc('Settings.GetSettingValue').execute(web_query)
    xbmc_webserver_enabled = result['result']['value']
    if not xbmc_webserver_enabled:
        xbmcgui.Dialog().ok(i18n('notice'), i18n('http_control'))
        return

    # get the port
    web_port = {"setting": "services.webserverport"}
    result = json_rpc('Settings.GetSettingValue').execute(web_port)
    xbmc_port = result['result']['value']
    log.debug("xbmc_port: {0}", xbmc_port)

    # get the user
    web_user = {"setting": "services.webserverusername"}
    result = json_rpc('Settings.GetSettingValue').execute(web_user)
    xbmc_username = result['result']['value']
    log.debug("xbmc_username: {0}", xbmc_username)

    # get the password
    web_pass = {"setting": "services.webserverpassword"}
    result = json_rpc('Settings.GetSettingValue').execute(web_pass)
    xbmc_password = result['result']['value']

    # ask to delete all textures
    question_result = xbmcgui.Dialog().yesno(i18n('delete'), i18n('delete_existing'))
    if question_result:
        pdialog = xbmcgui.DialogProgress()
        pdialog.create(i18n('deleting_textures'), "")
        index = 0

        json_result = json_rpc('Textures.GetTextures').execute()
        textures = json_result.get("result", {}).get("textures", [])
        log.debug("texture ids: {0}", textures)
        total = len(textures)
        for texture in textures:
            texture_id = texture["textureid"]
            params = {"textureid": int(texture_id)}
            json_result = json_rpc('Textures.RemoveTexture').execute(params)
            percentage = int((float(index) / float(total)) * 100)
            message = "%s of %s" % (index, total)
            pdialog.update(percentage, "%s" % (message))

            index += 1
            if pdialog.iscanceled():
                break

        del textures
        del pdialog

    question_result = xbmcgui.Dialog().yesno(i18n('cache_all_textures_title'), i18n('cache_all_textures'))
    if not question_result:
        return

    params = {"properties": ["url"]}
    json_result = json_rpc('Textures.GetTextures').execute(params)
    textures = json_result.get("result", {}).get("textures", [])

    texture_urls = set()
    for texture in textures:
        url = texture.get("url")
        url = urllib.unquote(url)
        url = url.replace("image://", "")
        url = url[0:-1]
        texture_urls.add(url)

    del textures
    del json_result

    url = ('{server}/emby/Users/{userid}/Items?' +
        '&Recursive=true' +
        '&IncludeItemTypes=Movie,Series,Episode,BoxSet' +
        '&ImageTypeLimit=1' +
        '&format=json')

    data_manager = DataManager()
    results = data_manager.GetContent(url)
    if results is None:
        results = []

    if isinstance(results, dict):
        results = results.get("Items")

    server = downloadUtils.getServer()
    missing_texture_urls = set()

    image_types = ["thumb", "poster", "banner", "clearlogo", "tvshow.poster", "tvshow.banner", "tvshow.landscape"]
    for item in results:
        art = getArt(item, server)
        for image_type in image_types:
            image_url = art[image_type]
            if image_url not in texture_urls and not image_url.endswith("&Tag=") and len(image_url) > 0:
                missing_texture_urls.add(image_url)

    log.debug("texture_urls: {0}", texture_urls)
    log.debug("missing_texture_urls: {0}", missing_texture_urls)
    log.debug("Number of existing textures: {0}", len(texture_urls))
    log.debug("Number of missing textures: {0}", len(missing_texture_urls))

    kodi_http_server = "localhost:" + str(xbmc_port)
    headers = {}
    if xbmc_password:
        auth = "%s:%s" % (xbmc_username, xbmc_password)
        headers = {'Authorization': 'Basic %s' % base64.b64encode(auth)}

    pdialog = xbmcgui.DialogProgress()
    pdialog.create(i18n('caching_textures'), "")
    total = len(missing_texture_urls)
    index = 1

    count_done = 0
    for get_url in missing_texture_urls:
        log.debug("texture_url: {0}", get_url)
        url = double_urlencode(get_url)
        kodi_texture_url = ("/image/image://%s" % url)
        log.debug("kodi_texture_url: {0}", kodi_texture_url)

        percentage = int((float(index) / float(total)) * 100)
        message = "%s of %s" % (index, total)
        pdialog.update(percentage, "%s" % (message))

        conn = httplib.HTTPConnection(kodi_http_server, timeout=20)
        conn.request(method="GET", url=kodi_texture_url, headers=headers)
        data = conn.getresponse()
        if data.status == 200:
            count_done += 1
        log.debug("Get Image Result: {0}", data.status)

        index += 1
        if pdialog.iscanceled():
            break

    pdialog.close()
    del pdialog

    report_text = i18n('existing_textures') + str(len(texture_urls)) + "\n"
    report_text += i18n('missing_textures') + str(len(missing_texture_urls)) + "\n"
    report_text += i18n('loaded_textures') + str(count_done)
    xbmcgui.Dialog().ok(i18n('done'), report_text)


def double_urlencode(text):
    text = single_urlencode(text)
    text = single_urlencode(text)
    return text


def single_urlencode(text):
    # urlencode needs a utf- string
    text = urllib.urlencode({'blahblahblah': text.encode('utf-8')})
    text = text[13:]
    return text.decode('utf-8') #return the result again as unicode


def send_event_notification(method, data):
    next_data = json.dumps(data)
    source_id = "embycon"
    data = '\\"[\\"{0}\\"]\\"'.format(binascii.hexlify(next_data))
    command = 'XBMC.NotifyAll({0}.SIGNAL,{1},{2})'.format(source_id, method, data)
    log.debug("Sending notification event data: {0}", command)
    xbmc.executebuiltin(command)

