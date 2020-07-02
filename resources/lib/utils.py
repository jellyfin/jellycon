# Gnu General Public License - see LICENSE.TXT
import xbmcaddon
import xbmc
import xbmcvfs

import string
import random
import urllib
import json
import base64
import time
import math
from datetime import datetime
import calendar
import re

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .clientinfo import ClientInformation

# hack to get datetime strptime loaded
throwaway = time.strptime('20110101', '%Y%m%d')

# define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


def get_emby_url(base_url, params):
    params["format"] = "json"
    param_list = []
    for key in params:
        if params[key] is not None:
            value = params[key]
            if isinstance(value, unicode):
                value = value.encode("utf8")
            else:
                value = str(value)
            param_list.append(key + "=" + urllib.quote_plus(value, safe="{}"))
    param_string = "&".join(param_list)
    return base_url + "?" + param_string


###########################################################################
class PlayUtils:

    @staticmethod
    def get_play_url(media_source):
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

            log.debug("playback_direct_path: {0}", direct_path)

            if xbmcvfs.exists(direct_path):
                playurl = direct_path
                playback_type = "0"

        # check if file can be direct streamed
        if can_direct_stream and playurl is None:
            direct_stream_path = media_source["DirectStreamUrl"]
            direct_stream_path = server + "/emby" + direct_stream_path
            if use_https and not verify_cert:
                direct_stream_path += "|verifypeer=false"
            playurl = direct_stream_path
            playback_type = "1"

        # check is file can be transcoded
        if can_transcode and playurl is None:
            transcode_stream_path = media_source["TranscodingUrl"]

            url_path, url_params = transcode_stream_path.split('?')

            params = url_params.split('&')
            log.debug("Streaming Params Before : {0}", params)

            # remove the audio and subtitle indexes
            # this will be replaced by user selection dialogs in Kodi
            params_to_remove = ["AudioStreamIndex", "SubtitleStreamIndex", "AudioBitrate"]
            reduced_params = []
            for param in params:
                param_bits = param.split("=")
                if param_bits[0] not in params_to_remove:
                    reduced_params.append(param)

            audio_playback_bitrate = addon_settings.getSetting("audio_playback_bitrate")
            audio_bitrate = int(audio_playback_bitrate) * 1000
            reduced_params.append("AudioBitrate=%s" % audio_bitrate)

            playback_max_width = addon_settings.getSetting("playback_max_width")
            reduced_params.append("MaxWidth=%s" % playback_max_width)

            log.debug("Streaming Params After : {0}", reduced_params)

            new_url_params = "&".join(reduced_params)

            transcode_stream_path = server + "/emby" + url_path + "?" + new_url_params

            if use_https and not verify_cert:
                transcode_stream_path += "|verifypeer=false"

            playurl = transcode_stream_path
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

    image_tags = item["ImageTags"]
    if image_tags is not None and image_tags["Primary"] is not None:
        # image_tag = image_tags["Primary"]
        art['thumb'] = downloadUtils.get_artwork(item, "Primary", server=server)

    item_type = item["Type"]

    if item_type == "Genre":
        art['poster'] = downloadUtils.get_artwork(item, "Primary", server=server)
    elif item_type == "Episode":
        art['tvshow.poster'] = downloadUtils.get_artwork(item, "Primary", parent=True, server=server)
        # art['poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
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
    text = urllib.urlencode({'blahblahblah': text.encode('utf-8')})
    text = text[13:]
    return text.decode('utf-8')  # return the result again as unicode


def send_event_notification(method, data):
    message_data = json.dumps(data)
    source_id = "embycon"
    base64_data = base64.b64encode(message_data)
    escaped_data = '\\"[\\"{0}\\"]\\"'.format(base64_data)
    command = 'XBMC.NotifyAll({0}.SIGNAL,{1},{2})'.format(source_id, method, escaped_data)
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


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
