from __future__ import division, absolute_import, print_function, unicode_literals

import sys
import xbmcgui
import xbmcplugin

from .loghandler import LazyLogger
from .item_functions import get_art
from .datamanager import DataManager

log = LazyLogger(__name__)


def show_server_sessions():
    log.debug("showServerSessions Called")

    handle = int(sys.argv[1])
    data_manager = DataManager()

    url = "/Users/{}".format(data_manager.api.user_id)
    results = data_manager.get_content(url)

    is_admin = results.get("Policy", {}).get("IsAdministrator", False)
    if not is_admin:
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
        return

    url = "/Sessions"
    results = data_manager.get_content(url)
    log.debug("session_info: {0}".format(results))

    if results is None:
        return

    list_items = []
    for session in results:
        device_name = session.get("DeviceName", "na")
        user_name = session.get("UserName", "na")
        client_name = session.get("Client", "na")
        client_version = session.get("ApplicationVersion", "na")

        play_state = session.get("PlayState", None)
        now_playing = session.get("NowPlayingItem", None)
        transcoding_info = session.get("TranscodingInfo", None)

        session_info = user_name + " - " + client_name
        user_session_details = ""

        percenatge_played = 0
        position_ticks = 0
        runtime = 0
        play_method = "na"

        if play_state is not None:
            position_ticks = play_state.get("PositionTicks", 0)
            play_method = play_state.get("PlayMethod", "na")

        art = {}
        if now_playing:
            server = settings.getSetting('server_address')
            art = get_art(now_playing, server)

            runtime = now_playing.get("RunTimeTicks", 0)
            if position_ticks > 0 and runtime > 0:
                percenatge_played = (position_ticks / float(runtime)) * 100.0
                percenatge_played = int(percenatge_played)

            session_info += " (" + now_playing.get("Name", "na") + " " + str(percenatge_played) + "%)"
            user_session_details += now_playing.get("Name", "na") + " " + str(percenatge_played) + "%" + "\n"

        else:
            session_info += " (idle)"
            user_session_details += "Idle" + "\n"

        transcoding_details = ""
        if transcoding_info:
            if not transcoding_info.get("IsVideoDirect", None):
                transcoding_details += "Video:" + transcoding_info.get("VideoCodec", "") + ":" + str(transcoding_info.get("Width", 0)) + "x" + str(transcoding_info.get("Height", 0)) + "\n"
            else:
                transcoding_details += "Video:direct\n"

            if not transcoding_info.get("IsAudioDirect", None):
                transcoding_details += "Audio:" + transcoding_info.get("AudioCodec", "") + ":" + str(transcoding_info.get("AudioChannels", 0)) + "\n"
            else:
                transcoding_details += "Audio:direct\n"

            transcoding_details += "Bitrate:" + str(transcoding_info.get("Bitrate", 0)) + "\n"

        list_item = xbmcgui.ListItem(label=session_info)
        list_item.setArt(art)

        user_session_details += device_name + "(" + client_version + ")\n"
        user_session_details += client_name + "\n"
        user_session_details += play_method + "\n"
        user_session_details += transcoding_details + "\n"

        info_labels = {}
        info_labels["duration"] = str(runtime / 10000000)
        info_labels["mediatype"] = "movie"
        info_labels["plot"] = user_session_details
        list_item.setInfo('video', info_labels)

        list_item.setProperty('TotalTime', str(runtime / 10000000))
        list_item.setProperty('ResumeTime', str(position_ticks / 10000000))
        list_item.setProperty("complete_percentage", str(percenatge_played))

        item_tuple = ("", list_item, False)
        list_items.append(item_tuple)

    xbmcplugin.setContent(handle, "movies")
    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
