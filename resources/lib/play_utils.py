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
from translation import i18n
from json_rpc import json_rpc

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()


def playFile(play_info):

    id = play_info.get("item_id")
    auto_resume = play_info.get("auto_resume")
    force_transcode = play_info.get("force_transcode")

    log.debug("playFile id(%s) resume(%s) force_transcode(%s)" % (id, auto_resume, force_transcode))

    settings = xbmcaddon.Addon('plugin.video.embycon')
    addon_path = settings.getAddonInfo('path')
    jump_back_amount = int(settings.getSetting("jump_back_amount"))

    server = downloadUtils.getServer()

    jsonData = downloadUtils.downloadUrl("{server}/emby/Users/{userid}/Items/" + id + "?format=json",
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
            log.debug("Resume Dialog Result: " + str(resume_result))

            # check system settings for play action
            # if prompt is set ask to set it to auto resume
            params = {"setting": "myvideos.selectaction"}
            setting_result = json_rpc('Settings.getSettingValue').execute(params)
            log.debug("Current Setting (myvideos.selectaction): %s" % setting_result)
            current_value = setting_result.get("result", None)
            if current_value is not None:
                current_value = current_value.get("value", -1)
            if current_value not in (2,3):
                return_value = xbmcgui.Dialog().yesno(i18n('extra_prompt'), i18n('turn_on_auto_resume?'))
                if return_value:
                    params = {"setting": "myvideos.selectaction", "value": 2}
                    json_rpc_result = json_rpc('Settings.setSettingValue').execute(params)
                    log.debug("Save Setting (myvideos.selectaction): %s" % json_rpc_result)

            if resume_result == 1:
                seekTime = 0
            elif resume_result == -1:
                return

    listitem_props = []
    playurl = None

    # check if strm file, path will contain contain strm contents
    if result.get('MediaSources'):
        source = result['MediaSources'][0]
        if source.get('Container') == 'strm':
            playurl, listitem_props = PlayUtils().getStrmDetails(result)

    if not playurl:
        playurl, playback_type = PlayUtils().getPlayUrl(id, result, force_transcode)

    log.debug("Play URL: " + playurl + " ListItem Properties: " + str(listitem_props))

    playback_type_string = "DirectPlay"
    if playback_type == "2":
        playback_type_string = "Transcode"
    elif playback_type == "1":
        playback_type_string = "DirectStream"

    home_window = HomeWindow()
    home_window.setProperty("PlaybackType_" + id, playback_type_string)

    # add the playback type into the overview
    if result.get("Overview", None) is not None:
        result["Overview"] = playback_type_string + "\n" + result.get("Overview")
    else:
        result["Overview"] = playback_type_string

    item_title = result.get("Name", i18n('missing_title'))
    add_episode_number = settings.getSetting('addEpisodeNumber') == 'true'
    if result.get("Type") == "Episode" and add_episode_number:
        episode_num = result.get("IndexNumber")
        if episode_num is not None:
            if episode_num < 10:
                episode_num = "0" + str(episode_num)
            else:
                episode_num = str(episode_num)
        else:
            episode_num = ""
        item_title =  episode_num + " - " + item_title

    list_item = xbmcgui.ListItem(label=item_title, path=playurl)

    list_item = setListItemProps(id, list_item, result, server, listitem_props, item_title)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    playlist.add(playurl, list_item)
    xbmc.Player().play(playlist)

    if seekTime == 0:
        return

    count = 0
    while not xbmc.Player().isPlaying():
        log.debug("Not playing yet...sleep for 1 sec")
        count = count + 1
        if count >= 10:
            return
        else:
            xbmc.Monitor().waitForAbort(1)

    seekTime = seekTime - jump_back_amount

    while xbmc.Player().getTime() < (seekTime - 5):
        # xbmc.Player().pause()
        xbmc.sleep(100)
        xbmc.Player().seekTime(seekTime)
        xbmc.sleep(100)
        # xbmc.Player().play()

def setListItemProps(id, listItem, result, server, extra_props, title):
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
    listItem.setProperty('id', result.get("Id"))

    for prop in extra_props:
        listItem.setProperty(prop[0], prop[1])

    # play info
    details = {
        'title': title,
        'plot': result.get("Overview")
    }

    if (eppNum > -1):
        details["episode"] = str(eppNum)

    if (seasonNum > -1):
        details["season"] = str(seasonNum)

    listItem.setInfo("Video", infoLabels=details)

    return listItem
