# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
import xbmc
import xbmcvfs

import binascii
import string
import random
import json
import base64
import time
import math
from datetime import datetime
import calendar
import re
from six import ensure_text, ensure_binary
from six.moves.urllib.parse import urlencode

from .downloadutils import DownloadUtils
from .loghandler import LazyLogger
from .clientinfo import ClientInformation

# hack to get datetime strptime loaded
throwaway = time.strptime('20110101', '%Y%m%d')

# define our global download utils
downloadUtils = DownloadUtils()
log = LazyLogger(__name__)


def get_jellyfin_url(base_url, params):
    params["format"] = "json"
    url_params = urlencode(params)
    # Filthy hack until I get around to reworking the network flow
    # It relies on {thing} strings in downloadutils.py
    url_params = url_params.replace('%7B', '{').replace('%7D', '}')
    return base_url + "?" + url_params


###########################################################################
class PlayUtils:

    @staticmethod
    def get_play_url(media_source, play_session_id):
        log.debug("get_play_url - media_source: {0}", media_source)

        # check if strm file Container
        if media_source.get('Container') == 'strm':
            log.debug("Detected STRM Container")
            playurl, listitem_props = PlayUtils().get_strm_details(media_source)
            if playurl is None:
                log.debug("Error, no strm content")
                return None, None, None
            else:
                return playurl, "0", listitem_props

        # get all the options
        addon_settings = xbmcaddon.Addon()
        server = downloadUtils.get_server()
        use_https = addon_settings.getSetting('protocol') == "1"
        verify_cert = addon_settings.getSetting('verify_cert') == 'true'
        allow_direct_file_play = addon_settings.getSetting('allow_direct_file_play') == 'true'

        can_direct_play = media_source["SupportsDirectPlay"]
        can_direct_stream = media_source["SupportsDirectStream"]
        can_transcode = media_source["SupportsTranscoding"]
        container = media_source["Container"]

        playurl = None
        playback_type = None

        # check if file can be directly played
        if allow_direct_file_play and can_direct_play:
            direct_path = media_source["Path"]
            direct_path = direct_path.replace("\\", "/")
            direct_path = direct_path.strip()

            # handle DVD structure
            if container == "dvd":
                direct_path = direct_path + "/VIDEO_TS/VIDEO_TS.IFO"
            elif container == "bluray":
                direct_path = direct_path + "/BDMV/index.bdmv"

            if direct_path.startswith("//"):
                direct_path = "smb://" + direct_path[2:]

            log.debug("playback_direct_path: {0}".format(direct_path))

            if xbmcvfs.exists(direct_path):
                playurl = direct_path
                playback_type = "0"

        # check if file can be direct streamed
        if can_direct_stream and playurl is None:
            item_id = media_source.get('Id')
            playurl = ("%s/Videos/%s/stream" +
                       "?static=true" +
                       "&PlaySessionId=%s" +
                       "&MediaSourceId=%s")
            playurl = playurl % (server, item_id, play_session_id, item_id)
            if use_https and not verify_cert:
                playurl += "|verifypeer=false"
            playback_type = "1"

        # check is file can be transcoded
        if can_transcode and playurl is None:
            item_id = media_source.get('Id')
            client_info = ClientInformation()
            device_id = client_info.get_device_id()
            user_token = downloadUtils.authenticate()
            playback_bitrate = addon_settings.getSetting("force_max_stream_bitrate")
            bitrate = int(playback_bitrate) * 1000
            playback_max_width = addon_settings.getSetting("playback_max_width")
            audio_codec = addon_settings.getSetting("audio_codec")
            audio_playback_bitrate = addon_settings.getSetting("audio_playback_bitrate")
            audio_bitrate = int(audio_playback_bitrate) * 1000
            audio_max_channels = addon_settings.getSetting("audio_max_channels")
            playback_video_force_8 = addon_settings.getSetting("playback_video_force_8") == "true"

            transcode_params = {
                "MediaSourceId": item_id,
                "DeviceId": device_id,
                "PlaySessionId": play_session_id,
                "api_key": user_token,
                "SegmentContainer": "ts",
                "VideoCodec": "h264",
                "VideoBitrate": bitrate,
                "MaxWidth": playback_max_width,
                "AudioCodec": audio_codec,
                "TranscodingMaxAudioChannels": audio_max_channels,
                "AudioBitrate": audio_bitrate
            }
            if playback_video_force_8:
                transcode_params.update({"MaxVideoBitDepth": "8"})

            transcode_path = urlencode(transcode_params)

            playurl = "%s/Videos/%s/master.m3u8?%s" % (server, item_id, transcode_path)

            if use_https and not verify_cert:
                playurl += "|verifypeer=false"

            playback_type = "2"

        return playurl, playback_type, []

    @staticmethod
    def get_strm_details(media_source):
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
            log.debug("STRM Line: {0}".format(line))
            if line.startswith('#KODIPROP:'):
                match = re.search('#KODIPROP:(?P<item_property>[^=]+?)=(?P<property_value>.+)', line)
                if match:
                    item_property = match.group('item_property')
                    property_value = match.group('property_value')
                    log.debug("STRM property found: {0} value: {1}".format(item_property, property_value))
                    listitem_props.append((item_property, property_value))
                else:
                    log.debug("STRM #KODIPROP incorrect format")
            elif line.startswith('#'):
                #  unrecognized, treat as comment
                log.debug("STRM unrecognized line identifier, ignored")
            elif line != '':
                playurl = line
                log.debug("STRM playback url found")

        log.debug("Playback URL: {0} ListItem Properties: {1}".format(playurl, listitem_props))
        return playurl, listitem_props


def get_checksum(item):
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


def get_art(item, server):
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

    image_tags = item.get("ImageTags", {})
    if image_tags and image_tags.get("Primary"):
        art['thumb'] = downloadUtils.get_artwork(item, "Primary", server=server)

    item_type = item["Type"]

    if item_type == "Genre":
        art['poster'] = downloadUtils.get_artwork(item, "Primary", server=server)
    elif item_type == "Episode":
        art['tvshow.poster'] = downloadUtils.get_artwork(item, "Primary", parent=True, server=server)
        art['tvshow.clearart'] = downloadUtils.get_artwork(item, "Art", parent=True, server=server)
        art['clearart'] = downloadUtils.get_artwork(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=True, server=server)
        art['clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.get_artwork(item, "Banner", parent=True, server=server)
        art['banner'] = downloadUtils.get_artwork(item, "Banner", parent=True, server=server)
        art['tvshow.landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=True, server=server)
        art['landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=True, server=server)
        art['tvshow.fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=True, server=server)
        art['fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=True, server=server)
    elif item_type == "Season":
        art['tvshow.poster'] = downloadUtils.get_artwork(item, "Primary", parent=True, server=server)
        art['season.poster'] = downloadUtils.get_artwork(item, "Primary", parent=False, server=server)
        art['poster'] = downloadUtils.get_artwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.get_artwork(item, "Art", parent=True, server=server)
        art['clearart'] = downloadUtils.get_artwork(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=True, server=server)
        art['clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.get_artwork(item, "Banner", parent=True, server=server)
        art['season.banner'] = downloadUtils.get_artwork(item, "Banner", parent=False, server=server)
        art['banner'] = downloadUtils.get_artwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=True, server=server)
        art['season.landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=False, server=server)
        art['landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=True, server=server)
        art['fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=True, server=server)
    elif item_type == "Series":
        art['tvshow.poster'] = downloadUtils.get_artwork(item, "Primary", parent=False, server=server)
        art['poster'] = downloadUtils.get_artwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.get_artwork(item, "Art", parent=False, server=server)
        art['clearart'] = downloadUtils.get_artwork(item, "Art", parent=False, server=server)
        art['tvshow.clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=False, server=server)
        art['clearlogo'] = downloadUtils.get_artwork(item, "Logo", parent=False, server=server)
        art['tvshow.banner'] = downloadUtils.get_artwork(item, "Banner", parent=False, server=server)
        art['banner'] = downloadUtils.get_artwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=False, server=server)
        art['landscape'] = downloadUtils.get_artwork(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=False, server=server)
        art['fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=False, server=server)
    elif item_type == "Movie" or item_type == "BoxSet":
        art['poster'] = downloadUtils.get_artwork(item, "Primary", server=server)
        art['landscape'] = downloadUtils.get_artwork(item, "Thumb", server=server)
        art['banner'] = downloadUtils.get_artwork(item, "Banner", server=server)
        art['clearlogo'] = downloadUtils.get_artwork(item, "Logo", server=server)
        art['clearart'] = downloadUtils.get_artwork(item, "Art", server=server)
        art['discart'] = downloadUtils.get_artwork(item, "Disc", server=server)

    art['fanart'] = downloadUtils.get_artwork(item, "Backdrop", server=server)
    if not art['fanart']:
        art['fanart'] = downloadUtils.get_artwork(item, "Backdrop", parent=True, server=server)

    return art


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def double_urlencode(text):
    text = single_urlencode(text)
    text = single_urlencode(text)
    return text


def single_urlencode(text):
    # urlencode needs a utf- string
    text = urlencode({'blahblahblah': text.encode('utf-8')})
    text = text[13:]
    return text.decode('utf-8')  # return the result again as unicode


def send_event_notification(method, data=None, hexlify=False):
    '''
    Send events through Kodi's notification system
    '''
    data = data or {}

    if hexlify:
        # Used exclusively for the upnext plugin
        data = ensure_text(binascii.hexlify(ensure_binary(json.dumps(data))))
    sender = 'plugin.video.jellycon'
    data = '"[%s]"' % json.dumps(data).replace('"', '\\"')

    xbmc.executebuiltin('NotifyAll(%s, %s, %s)' % (sender, method, data))


def datetime_from_string(time_string):

    if time_string[-1:] == "Z":
        time_string = re.sub("[0-9]{1}Z", " UTC", time_string)
    elif time_string[-6:] == "+00:00":
        time_string = re.sub("[0-9]{1}\+00:00", " UTC", time_string)
    log.debug("New Time String : {0}".format(time_string))

    start_time = time.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")
    dt = datetime(*(start_time[0:6]))
    timestamp = calendar.timegm(dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    local_dt.replace(microsecond=dt.microsecond)
    return local_dt


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
