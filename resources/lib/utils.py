# Gnu General Public License - see LICENSE.TXT
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc

import string
import random
import urllib
import json
import binascii
import time
from datetime import datetime
import _strptime
import calendar
import re

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .clientinfo import ClientInformation

# hack to get datetime strptime loaded
throwaway = time.strptime('20110101','%Y%m%d')

# define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, media_source, force_transcode, play_session_id):
        log.debug("getPlayUrl")
        addonSettings = xbmcaddon.Addon()
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


def getArt(item, server):
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
        art['thumb'] = downloadUtils.getArtwork(item, "Primary", server=server)

    item_type = item["Type"]

    if item_type == "Genre":
        art['poster'] = downloadUtils.getArtwork(item, "Primary", server=server)
    elif item_type == "Episode":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
        #art['poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Art", parent=True, server=server)
        art['clearart'] = downloadUtils.getArtwork(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=True, server=server)
        art['banner'] = downloadUtils.getArtwork(item, "Banner", parent=True, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['tvshow.fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)
    elif item_type == "Season":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
        art['season.poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Art", parent=True, server=server)
        art['clearart'] = downloadUtils.getArtwork(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=True, server=server)
        art['season.banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['season.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)
    elif item_type == "Series":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Art", parent=False, server=server)
        art['clearart'] = downloadUtils.getArtwork(item, "Art", parent=False, server=server)
        art['tvshow.clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=False, server=server)
        art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", parent=False, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=False, server=server)
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=False, server=server)
    elif item_type == "Movie" or item_type == "BoxSet":
        art['poster'] = downloadUtils.getArtwork(item, "Primary", server=server)
        art['landscape'] = downloadUtils.getArtwork(item, "Thumb", server=server)
        art['banner'] = downloadUtils.getArtwork(item, "Banner", server=server)
        art['clearlogo'] = downloadUtils.getArtwork(item, "Logo", server=server)
        art['clearart'] = downloadUtils.getArtwork(item, "Art", server=server)
        art['discart'] = downloadUtils.getArtwork(item, "Disc", server=server)

    art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", server=server)
    if not art['fanart']:
        art['fanart'] = downloadUtils.getArtwork(item, "Backdrop", parent=True, server=server)

    return art


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


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


def datetime_from_string(time_string):

    if time_string[-1:] == "Z":
        time_string = re.sub("[0-9]{1}Z", " UTC", time_string)
    elif time_string[-6:] == "+00:00":
        time_string = re.sub("[0-9]{1}\+00:00", " UTC", time_string)
    log.debug("New Time String : {0}", time_string)

    start_time = time.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")
    dt = datetime(*(start_time[0:6]))
    timestamp = calendar.timegm(dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    local_dt.replace(microsecond=dt.microsecond)
    return local_dt
