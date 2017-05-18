# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
from downloadutils import DownloadUtils
import urllib
import sys
from simple_logging import SimpleLogging
from clientinfo import ClientInformation

#define our global download utils
downloadUtils = DownloadUtils()
log = SimpleLogging("EmbyCon." + __name__)

###########################################################################
class PlayUtils():
    def getPlayUrl(self, id, result):
        log.info("getPlayUrl")
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        playback_type = addonSettings.getSetting("playback_type")
        playback_bitrate = addonSettings.getSetting("playback_bitrate")
        server = addonSettings.getSetting('ipaddress') + ":" + addonSettings.getSetting('port')
        log.info("playback_type: " + playback_type)
        playurl = None

        # do direct path playback
        if playback_type == "0":
            playurl = result.get("Path")

            # handle DVD structure
            if (result.get("VideoType") == "Dvd"):
                playurl = playurl + "/VIDEO_TS/VIDEO_TS.IFO"
            elif (result.get("VideoType") == "BluRay"):
                playurl = playurl + "/BDMV/index.bdmv"

            # add smb creds
            if addonSettings.getSetting('smbusername') == '':
                playurl = playurl.replace("\\\\", "smb://")
            else:
                playurl = playurl.replace("\\\\", "smb://" + addonSettings.getSetting(
                    'smbusername') + ':' + addonSettings.getSetting('smbpassword') + '@')

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


def getKodiVersion():
    version = 0.0
    jsonData = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')

    result = json.loads(jsonData)

    try:
        result = result.get("result")
        versionData = result.get("version")
        version = float(str(versionData.get("major")) + "." + str(versionData.get("minor")))
        log.info("Version : " + str(version) + " - " + str(versionData))
    except:
        version = 0.0
        log.error("Version Error : RAW Version Data : " + str(result))

    return version

def getDetailsString():
    detailsString = "EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks,MediaStreams,Overview,Etag"
    #detailsString = "EpisodeCount,SeasonCount,Path,Genres,CumulativeRunTimeTicks"
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
