# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

from datetime import timedelta
import time
import json

from simple_logging import SimpleLogging
from downloadutils import DownloadUtils
from resume_dialog import ResumeDialog
from utils import PlayUtils, getArt
from kodi_utils import HomeWindow

log = SimpleLogging("EmbyCon." + __name__)
__addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
__language__ = __addon__.getLocalizedString
downloadUtils = DownloadUtils()

def playFile(id, auto_resume):
    log.info("playFile id(" + str(id) + ") resume(" + str(auto_resume) + ")")

    userid = downloadUtils.getUserId()

    settings = xbmcaddon.Addon(id='plugin.video.embycon')
    addon_path = settings.getAddonInfo('path')
    playback_type = settings.getSetting("playback_type")

    port = settings.getSetting('port')
    host = settings.getSetting('ipaddress')
    server = host + ":" + port

    jsonData = downloadUtils.downloadUrl("http://" + server + "/emby/Users/" + userid + "/Items/" + id + "?format=json",
                                         suppress=False, popup=1)
    result = json.loads(jsonData)

    seekTime = 0
    auto_resume = int(auto_resume)

    if auto_resume != -1:
        seekTime = (auto_resume / 1000) / 10000
    else:
        userData = result.get("UserData")
        if userData.get("PlaybackPositionTicks") != 0:
            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            seekTime = reasonableTicks / 10000
            displayTime = str(timedelta(seconds=seekTime))

            resumeDialog = ResumeDialog("ResumeDialog.xml", addon_path, "default", "720p")
            resumeDialog.setResumeTime("Resume from " + displayTime)
            resumeDialog.doModal()
            resume_result = resumeDialog.getResumeAction()
            del resumeDialog

            log.info("Resume Dialog Result: " + str(resume_result))

            if resume_result == 1:
                seekTime = 0
            elif resume_result == -1:
                return

    playurl = PlayUtils().getPlayUrl(id, result)
    log.info("Play URL: " + playurl)

    playback_type_string = "DirectPlay"
    if playback_type == "1":
        playback_type_string = "DirectStream"
    elif playback_type == "2":
        playback_type_string = "Transcode"

    home_window = HomeWindow()
    home_window.setProperty("PlaybackType_" + id, playback_type_string)

    listItem = xbmcgui.ListItem(label=result.get("Name", __language__(30280)), path=playurl)

    listItem = setListItemProps(id, listItem, result, server)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    playlist.add(playurl, listItem)
    xbmc.Player().play(playlist)

    if seekTime == 0:
        return

    count = 0
    while not xbmc.Player().isPlaying():
        log.info("Not playing yet...sleep for 1 sec")
        count = count + 1
        if count >= 10:
            return
        else:
            time.sleep(1)

    while xbmc.Player().getTime() < (seekTime - 5):
        #xbmc.Player().pause()
        xbmc.sleep(100)
        xbmc.Player().seekTime(seekTime)
        xbmc.sleep(100)
        #xbmc.Player().play()


def setListItemProps(id, listItem, result, server):
    # set up item and item info
    thumbID = id
    eppNum = -1
    seasonNum = -1

    art = getArt(result, server=server)
    listItem.setIconImage(art['thumb'])  # back compat
    listItem.setProperty('fanart_image', art['fanart'])  # back compat
    listItem.setProperty('discart', art['discart'])  # not avail to setArt
    listItem.setArt(art)

    listItem.setProperty('IsPlayable', 'true')
    listItem.setProperty('IsFolder', 'false')

    # play info
    details = {
        'title': result.get("Name", __language__(30280)),
        'plot': result.get("Overview")
    }

    if (eppNum > -1):
        details["episode"] = str(eppNum)

    if (seasonNum > -1):
        details["season"] = str(seasonNum)

    listItem.setInfo("Video", infoLabels=details)

    return listItem