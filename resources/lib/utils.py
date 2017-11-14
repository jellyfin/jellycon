# Gnu General Public License - see LICENSE.TXT
import xbmcaddon
import re
import encodings
import string
import random

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from clientinfo import ClientInformation

# define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, result, force_transcode, play_session_id):
        log.debug("getPlayUrl")
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        playback_type = addonSettings.getSetting("playback_type")
        server = downloadUtils.getServer()
        log.debug("playback_type: " + playback_type)
        if force_transcode:
            log.debug("playback_type: FORCED_TRANSCODE")
        playurl = None
        log.debug("play_session_id: " + play_session_id)

        is_h265 = False
        streams = result.get("MediaStreams", [])
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
            log.debug("playback_bitrate: " + playback_bitrate)

            playback_max_width = addonSettings.getSetting("playback_max_width")
            playback_video_force_8 = addonSettings.getSetting("playback_video_force_8") == "true"

            clientInfo = ClientInformation()
            deviceId = clientInfo.getDeviceId()
            bitrate = int(playback_bitrate) * 1000
            user_token = downloadUtils.authenticate()

            playurl = (
                "%s/emby/Videos/%s/master.m3u8?MediaSourceId=%s&PlaySessionId=%s&VideoCodec=h264&AudioCodec=ac3&MaxAudioChannels=6&deviceId=%s&VideoBitrate=%s&DeviceId=%s"
                % (server, id, id, play_session_id, deviceId, bitrate))

            playurl = playurl + "&maxWidth=" + playback_max_width

            if playback_video_force_8:
                playurl = playurl + "&MaxVideoBitDepth=8"

            playurl = playurl + "&api_key=" + user_token

        # do direct path playback
        elif playback_type == "0":
            playurl = result.get("Path")

            # handle DVD structure
            if (result.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
            elif (result.get("VideoType") == "BluRay"):
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
            playurl = "%s/emby/Videos/%s/stream?static=true&PlaySessionId=%s" % (server, id, play_session_id)
            user_token = downloadUtils.authenticate()
            playurl = playurl + "&api_key=" + user_token

        log.debug("Playback URL: " + playurl)
        return playurl.encode('utf-8'), playback_type

    def getStrmDetails(self, result):
        playurl = None
        listitem_props = []

        source = result['MediaSources'][0]
        contents = source.get('Path').encode('utf-8')  # contains contents of strm file with linebreaks

        line_break = '\r'
        if '\r\n' in contents:
            line_break += '\n'

        lines = contents.split(line_break)
        for line in lines:
            line = line.strip()
            if line.startswith('#KODIPROP:'):
                match = re.search('#KODIPROP:(?P<item_property>[^=]+?)=(?P<property_value>.+)', line)
                if match:
                    listitem_props.append((match.group('item_property'), match.group('property_value')))
            elif line != '':
                playurl = line

        log.debug("Playback URL: " + playurl + " ListItem Properties: " + str(listitem_props))
        return playurl, listitem_props


def getDetailsString():

    addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
    include_media = addonSettings.getSetting("include_media") == "true"
    include_people = addonSettings.getSetting("include_people") == "true"
    include_overview = addonSettings.getSetting("include_overview") == "true"

    detailsString = "DateCreated,EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks,Etag"

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
        'tvshow.poster': '',
        'tvshow.clearart': '',
        'tvshow.banner': '',
        'tvshow.landscape': ''
    }
    item_id = item.get("Id")

    image_id = item_id
    imageTags = item.get("ImageTags")
    if (imageTags is not None) and (imageTags.get("Primary") is not None):
        image_tag = imageTags.get("Primary")
        if widget:
            art['thumb'] = downloadUtils.imageUrl(image_id, "Primary", 0, 400, 400, image_tag, server=server)
        else:
            art['thumb'] = downloadUtils.getArtwork(item, "Primary", server=server)

    if item.get("Type") == "Episode" or item.get("Type") == "Season":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=True, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
    elif item.get("Type") == "Series":
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = downloadUtils.getArtwork(item, "Logo", parent=False, server=server)
        art['tvshow.banner'] = downloadUtils.getArtwork(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = downloadUtils.getArtwork(item, "Thumb", parent=False, server=server)

    if item.get("Type") == "Episode":
        art['thumb'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", server=server)
        art['landscape'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
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