from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import sys

import xbmcgui
import xbmcplugin
import xbmcaddon

from .jellyfin import api
from .lazylogger import LazyLogger
from .item_functions import get_art
from .utils import load_user_details

log = LazyLogger(__name__)


def show_server_sessions():
    log.debug("showServerSessions Called")

    handle = int(sys.argv[1])

    user_details = load_user_details()
    url = "/Users/{}".format(user_details.get('user_id'))
    results = api.get(url)

    is_admin = results.get("Policy", {}).get("IsAdministrator", False)
    if not is_admin:
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
        return

    url = "/Sessions"
    results = api.get(url)
    log.debug("session_info: {0}".format(results))

    if results is None:
        return

    list_items = []
    settings = xbmcaddon.Addon()
    server = settings.getSetting('server_address')
    for session in results:
        device_name = session.get("DeviceName", "na")
        user_name = session.get("UserName", "na")
        client_name = session.get("Client", "na")
        client_version = session.get("ApplicationVersion", "na")

        play_state = session.get("PlayState", None)
        now_playing = session.get("NowPlayingItem", None)
        transcoding_info = session.get("TranscodingInfo", None)

        session_info = "{} - {}".format(user_name, client_name)
        user_session_details = ""

        percentage_played = 0
        position_ticks = 0
        runtime = 0
        play_method = "na"

        if play_state is not None:
            position_ticks = play_state.get("PositionTicks", 0)
            play_method = play_state.get("PlayMethod", "na")

        art = {}
        if now_playing:
            art = get_art(now_playing, server)

            runtime = now_playing.get("RunTimeTicks", 0)
            if position_ticks > 0 and runtime > 0:
                percentage_played = (position_ticks / float(runtime)) * 100.0
                percentage_played = int(percentage_played)

            session_info += " {} {}%".format(
                now_playing.get("Name", "na"), percentage_played
            )
            user_session_details += "{} {}%\n".format(
                now_playing.get("Name", "na"), percentage_played
            )

        else:
            session_info += " (idle)"
            user_session_details += "Idle\n"

        transcoding_details = ""
        if transcoding_info:
            if not transcoding_info.get("IsVideoDirect", None):
                transcoding_details += "Video:{}:{}x{}\n".format(
                    transcoding_info.get("VideoCodec", ""),
                    transcoding_info.get("Width", 0),
                    transcoding_info.get("Height", 0)
                )
            else:
                transcoding_details += "Video:direct\n"

            if not transcoding_info.get("IsAudioDirect", None):
                transcoding_details += "Audio:{}:{}\n".format(
                    transcoding_info.get("AudioCodec", ""),
                    transcoding_info.get("AudioChannels", 0)
                )
            else:
                transcoding_details += "Audio:direct\n"

            transcoding_details += "Bitrate:{}\n".format(
                transcoding_info.get("Bitrate", 0)
            )

        list_item = xbmcgui.ListItem(label=session_info)
        list_item.setArt(art)

        user_session_details += "{}({})\n".format(device_name, client_version)
        user_session_details += "{}\n".format(client_name)
        user_session_details += "{}\n".format(play_method)
        user_session_details += "{}\n".format(transcoding_details)

        info_labels = {}
        info_labels["duration"] = str(runtime / 10000000)
        info_labels["mediatype"] = "movie"
        info_labels["plot"] = user_session_details
        list_item.setInfo('video', info_labels)

        list_item.setProperty('TotalTime', str(runtime / 10000000))
        list_item.setProperty('ResumeTime', str(position_ticks / 10000000))
        list_item.setProperty("complete_percentage", str(percentage_played))

        item_tuple = ("", list_item, False)
        list_items.append(item_tuple)

    xbmcplugin.setContent(handle, "movies")
    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
