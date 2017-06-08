# Gnu General Public License - see LICENSE.TXT
import xbmc
import xbmcaddon
import xbmcvfs

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from clientinfo import ClientInformation

# define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging(__name__)


###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, result):
        log.info("getPlayUrl")
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        playback_type = addonSettings.getSetting("playback_type")
        playback_bitrate = addonSettings.getSetting("playback_bitrate")
        server = addonSettings.getSetting('ipaddress') + ":" + addonSettings.getSetting('port')
        smb_username = addonSettings.getSetting('smbusername')
        smb_password = addonSettings.getSetting('smbpassword')
        log.info("playback_type: " + playback_type)
        playurl = None

        # check if strm file, will contain contain playback url
        if result.get('MediaSources'):
            source = result['MediaSources'][0]
            if source.get('Container') == 'strm':
                strm_path = xbmc.translatePath('special://temp/')
                strm_file = xbmc.translatePath('special://temp/embycon.strm')
                if not xbmcvfs.exists(strm_path):
                    xbmcvfs.mkdirs(strm_path)
                f = xbmcvfs.File(strm_file, mode='w')  # create a temp local .strm, required for inputstream(strm contains listitem properties and path)
                contents = source.get('Path').encode('utf-8')  # contains contents of strm file with linebreaks
                f.write(contents)
                f.close()
                playurl = strm_file if xbmcvfs.exists(strm_file) else None
                if playurl:
                    return playurl

        # do direct path playback
        if playback_type == "0":
            playurl = result.get("Path")

            # handle DVD structure
            if (result.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
            elif (result.get("VideoType") == "BluRay"):
                playurl = playurl + "/BDMV/index.bdmv"

            # add smb creds
            if smb_username == '':
                playurl = playurl.replace("\\\\", "smb://")
            else:
                playurl = playurl.replace("\\\\", "smb://" + smb_username + ':' + smb_password + '@')

            playurl = playurl.replace("\\", "/")

        # do direct http streaming playback
        elif playback_type == "1":
            playurl = "http://%s/emby/Videos/%s/stream?static=true" % (server, id)
            user_token = downloadUtils.authenticate()
            playurl = playurl + "&api_key=" + user_token

        # do transcode http streaming playback
        elif playback_type == "2":
            log.info("playback_bitrate: " + playback_bitrate)

            clientInfo = ClientInformation()
            deviceId = clientInfo.getDeviceId()
            bitrate = int(playback_bitrate) * 1000
            user_token = downloadUtils.authenticate()

            playurl = (
                "http://%s/emby/Videos/%s/master.m3u8?MediaSourceId=%s&VideoCodec=h264&AudioCodec=ac3&MaxAudioChannels=6&deviceId=%s&VideoBitrate=%s"
                % (server, id, id, deviceId, bitrate))

            playurl = playurl + "&api_key=" + user_token

        log.info("Playback URL: " + playurl)
        return playurl.encode('utf-8')


def getDetailsString():

    addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
    include_media = addonSettings.getSetting("include_media") == "true"
    include_people = addonSettings.getSetting("include_people") == "true"
    include_overwiew = addonSettings.getSetting("include_overview") == "true"

    detailsString = "EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks,Etag"

    if include_media:
        detailsString += ",MediaStreams"

    if include_people:
        detailsString += ",People"

    if include_overwiew:
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
        'tvshow.poster': ''
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

    if item.get("Type") == "Episode":
        art['thumb'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", server=server)
        art['landscape'] = art['thumb'] if art['thumb'] else downloadUtils.getArtwork(item, "Thumb", parent=True, server=server)
        art['tvshow.poster'] = downloadUtils.getArtwork(item, "Primary", parent=True, server=server)
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
