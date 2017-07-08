
import json
import sys
import xbmcgui
import xbmcplugin

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging

log = SimpleLogging(__name__)

def showServerSessions():
    log.debug("showServerSessions Called")

    handle = int(sys.argv[1])
    downloadUtils = DownloadUtils()
    url = "{server}/emby/Sessions"
    result_data = downloadUtils.downloadUrl(url)
    results = json.loads(result_data)

    if results is None:
        return

    list_items = []
    for session in results:
        device_name = session.get("DeviceName", "na")
        user_name = session.get("UserName", "na")
        client_name = session.get("Client", "na")

        session_info = device_name + " - " + user_name + " - " + client_name

        # playstate
        percenatge_played = 0
        play_state = session.get("PlayState", None)
        if play_state is not None:
            runtime = 0
            media_id = play_state.get("MediaSourceId", None)
            log.debug("Media ID " + str(media_id))
            if media_id is not None:
                jsonData = downloadUtils.downloadUrl("{server}/emby/Users/{userid}/Items/" +
                                                        media_id + "?format=json",
                                                        suppress=False, popup=1)
                media_info = json.loads(jsonData)
                log.debug("Media Info " + str(media_info))
                runtime = media_info.get("RunTimeTicks", 0)
                log.debug("Media Runtime " + str(runtime))

            position_ticks = play_state.get("PositionTicks", 0)
            log.debug("Media PositionTicks " + str(position_ticks))
            if position_ticks > 0 and runtime > 0:
                percenatge_played = (position_ticks / float(runtime)) * 100.0
                percenatge_played = int(percenatge_played)

        now_playing = session.get("NowPlayingItem", None)
        log.debug("NOW_PLAYING: " + str(now_playing))
        if now_playing is not None:
            session_info += " (" + now_playing.get("Name", "na") + " " + str(percenatge_played) + "%)"

        log.debug(session_info)
        list_item = xbmcgui.ListItem(label=session_info)
        item_tuple = ("", list_item, False)
        list_items.append(item_tuple)

    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
