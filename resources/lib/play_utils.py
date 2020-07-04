# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

from datetime import timedelta
import json
import os
import base64

from .simple_logging import SimpleLogging
from .downloadutils import DownloadUtils
from .resume_dialog import ResumeDialog
from .utils import PlayUtils, get_art, send_event_notification, convert_size
from .kodi_utils import HomeWindow
from .translation import string_load
from .datamanager import DataManager, clear_old_cache_data
from .item_functions import extract_item_info, add_gui_item
from .clientinfo import ClientInformation
from .functions import delete
from .cache_images import CacheArtwork
from .picture_viewer import PictureViewer
from .tracking import timer
from .playnext import PlayNextDialog

log = SimpleLogging(__name__)
download_utils = DownloadUtils()


def play_all_files(items, monitor, play_items=True):
    log.debug("playAllFiles called with items: {0}", items)
    server = download_utils.get_server()

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    for item in items:

        item_id = item.get("Id")

        # get playback info
        playback_info = download_utils.get_item_playback_info(item_id, False)
        if playback_info is None:
            log.debug("playback_info was None, could not get MediaSources so can not play!")
            return
        if playback_info.get("ErrorCode") is not None:
            error_string = playback_info.get("ErrorCode")
            xbmcgui.Dialog().notification(string_load(30316),
                                          error_string,
                                          icon="special://home/addons/plugin.video.jellycon/icon.png")
            return

        play_session_id = playback_info.get("PlaySessionId")

        # select the media source to use
        sources = playback_info.get('MediaSources')

        selected_media_source = sources[0]
        source_id = selected_media_source.get("Id")

        playurl, playback_type, listitem_props = PlayUtils().get_play_url(selected_media_source, play_session_id)
        log.info("Play URL: {0} PlaybackType: {1} ListItem Properties: {2}", playurl, playback_type, listitem_props)

        if playurl is None:
            return

        playback_type_string = "DirectPlay"
        if playback_type == "2":
            playback_type_string = "Transcode"
        elif playback_type == "1":
            playback_type_string = "DirectStream"

        # add the playback type into the overview
        if item.get("Overview", None) is not None:
            item["Overview"] = playback_type_string + "\n" + item.get("Overview")
        else:
            item["Overview"] = playback_type_string

        # add title decoration is needed
        item_title = item.get("Name", string_load(30280))
        list_item = xbmcgui.ListItem(label=item_title)

        # add playurl and data to the monitor
        data = {}
        data["item_id"] = item_id
        data["source_id"] = source_id
        data["playback_type"] = playback_type_string
        data["play_session_id"] = play_session_id
        data["play_action_type"] = "play_all"
        monitor.played_information[playurl] = data
        log.debug("Add to played_information: {0}", monitor.played_information)

        list_item.setPath(playurl)
        list_item = set_list_item_props(item_id, list_item, item, server, listitem_props, item_title)

        playlist.add(playurl, list_item)

    if play_items:
        xbmc.Player().play(playlist)
        return None
    else:
        return playlist


def play_list_of_items(id_list, monitor):
    log.debug("Loading  all items in the list")
    data_manager = DataManager()
    items = []

    for item_id in id_list:
        url = "{server}/Users/{userid}/Items/%s?format=json"
        url = url % (item_id,)
        result = data_manager.get_content(url)
        if result is None:
            log.debug("Playfile item was None, so can not play!")
            return
        items.append(result)

    return play_all_files(items, monitor)


def add_to_playlist(play_info, monitor):
    log.debug("Adding item to playlist : {0}", play_info)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    server = download_utils.get_server()

    item_id = play_info.get("item_id")

    url = "{server}/Users/{userid}/Items/%s?format=json"
    url = url % (item_id,)
    data_manager = DataManager()
    item = data_manager.get_content(url)
    if item is None:
        log.debug("Playfile item was None, so can not play!")
        return

    # get playback info
    playback_info = download_utils.get_item_playback_info(item_id, False)
    if playback_info is None:
        log.debug("playback_info was None, could not get MediaSources so can not play!")
        return
    if playback_info.get("ErrorCode") is not None:
        error_string = playback_info.get("ErrorCode")
        xbmcgui.Dialog().notification(string_load(30316),
                                      error_string,
                                      icon="special://home/addons/plugin.video.jellycon/icon.png")
        return

    # play_session_id = id_generator()
    play_session_id = playback_info.get("PlaySessionId")

    # select the media source to use
    # sources = item.get("MediaSources")
    sources = playback_info.get('MediaSources')

    selected_media_source = sources[0]
    source_id = selected_media_source.get("Id")

    playurl, playback_type, listitem_props = PlayUtils().get_play_url(selected_media_source, play_session_id)
    log.info("Play URL: {0} PlaybackType: {1} ListItem Properties: {2}", playurl, playback_type, listitem_props)

    if playurl is None:
        return

    playback_type_string = "DirectPlay"
    if playback_type == "2":
        playback_type_string = "Transcode"
    elif playback_type == "1":
        playback_type_string = "DirectStream"

    # add the playback type into the overview
    if item.get("Overview", None) is not None:
        item["Overview"] = playback_type_string + "\n" + item.get("Overview")
    else:
        item["Overview"] = playback_type_string

    # add title decoration is needed
    item_title = item.get("Name", string_load(30280))
    list_item = xbmcgui.ListItem(label=item_title)

    # add playurl and data to the monitor
    data = {}
    data["item_id"] = item_id
    data["source_id"] = source_id
    data["playback_type"] = playback_type_string
    data["play_session_id"] = play_session_id
    data["play_action_type"] = "play_all"
    monitor.played_information[playurl] = data
    log.debug("Add to played_information: {0}", monitor.played_information)

    list_item.setPath(playurl)
    list_item = set_list_item_props(item_id, list_item, item, server, listitem_props, item_title)

    playlist.add(playurl, list_item)


def get_playback_intros(item_id):
    log.debug("get_playback_intros")
    data_manager = DataManager()
    url = "{server}/Users/{userid}/Items/%s/Intros" % item_id
    intro_items = data_manager.get_content(url)

    if intro_items is None:
        log.debug("get_playback_intros failed!")
        return

    into_list = []
    intro_items = intro_items["Items"]
    for into in intro_items:
        into_list.append(into)

    return into_list


@timer
def play_file(play_info, monitor):
    item_id = play_info.get("item_id")

    home_window = HomeWindow()
    last_url = home_window.get_property("last_content_url")
    if last_url:
        home_window.set_property("skip_cache_for_" + last_url, "true")

    action = play_info.get("action", "play")
    if action == "add_to_playlist":
        add_to_playlist(play_info, monitor)
        return

    # if this is a list of items them add them all to the play list
    if isinstance(item_id, list):
        return play_list_of_items(item_id, monitor)

    auto_resume = play_info.get("auto_resume", "-1")
    force_transcode = play_info.get("force_transcode", False)
    media_source_id = play_info.get("media_source_id", "")
    subtitle_stream_index = play_info.get("subtitle_stream_index", None)
    audio_stream_index = play_info.get("audio_stream_index", None)

    log.debug("playFile id({0}) resume({1}) force_transcode({2})", item_id, auto_resume, force_transcode)

    settings = xbmcaddon.Addon()
    addon_path = settings.getAddonInfo('path')
    force_auto_resume = settings.getSetting('forceAutoResume') == 'true'
    jump_back_amount = int(settings.getSetting("jump_back_amount"))
    play_cinema_intros = settings.getSetting('play_cinema_intros') == 'true'

    server = download_utils.get_server()

    url = "{server}/Users/{userid}/Items/%s?format=json" % (item_id,)
    data_manager = DataManager()
    result = data_manager.get_content(url)
    log.debug("Playfile item: {0}", result)

    if result is None:
        log.debug("Playfile item was None, so can not play!")
        return

    # if this is a season, playlist or album then play all items in that parent
    if result.get("Type") in ["Season", "MusicAlbum", "Playlist"]:
        log.debug("PlayAllFiles for parent item id: {0}", item_id)
        url = ('{server}/Users/{userid}/items' +
               '?ParentId=%s' +
               '&Fields=MediaSources' +
               '&format=json')
        url = url % (item_id,)
        result = data_manager.get_content(url)
        log.debug("PlayAllFiles items: {0}", result)

        # process each item
        items = result["Items"]
        if items is None:
            items = []
        return play_all_files(items, monitor)

    # if this is a program from live tv epg then play the actual channel
    if result.get("Type") == "Program":
        channel_id = result.get("ChannelId")
        url = "{server}/Users/{userid}/Items/%s?format=json" % (channel_id,)
        result = data_manager.get_content(url)
        item_id = result["Id"]

    if result.get("Type") == "Photo":
        play_url = "%s/Items/%s/Images/Primary"
        play_url = play_url % (server, item_id)

        plugin_path = xbmc.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('path')))
        action_menu = PictureViewer("PictureViewer.xml", plugin_path, "default", "720p")
        action_menu.setPicture(play_url)
        action_menu.doModal()
        return

    # get playback info from the server using the device profile
    playback_info = download_utils.get_item_playback_info(item_id, force_transcode)
    if playback_info is None:
        log.debug("playback_info was None, could not get MediaSources so can not play!")
        return
    if playback_info.get("ErrorCode") is not None:
        error_string = playback_info.get("ErrorCode")
        xbmcgui.Dialog().notification(string_load(30316),
                                      error_string,
                                      icon="special://home/addons/plugin.video.jellycon/icon.png")
        return

    play_session_id = playback_info.get("PlaySessionId")

    # select the media source to use
    media_sources = playback_info.get('MediaSources')
    selected_media_source = None

    if media_sources is None or len(media_sources) == 0:
        log.debug("Play Failed! There is no MediaSources data!")
        return

    elif len(media_sources) == 1:
        selected_media_source = media_sources[0]

    elif media_source_id != "":
        for source in media_sources:
            if source.get("Id", "na") == media_source_id:
                selected_media_source = source
                break

    elif len(media_sources) > 1:
        items = []
        for source in media_sources:
            label = source.get("Name", "na")
            label2 = __build_label2_from(source)
            items.append(xbmcgui.ListItem(label=label, label2=label2))
        dialog = xbmcgui.Dialog()
        resp = dialog.select(string_load(30309), items, useDetails=True)
        if resp > -1:
            selected_media_source = media_sources[resp]
        else:
            log.debug("Play Aborted, user did not select a MediaSource")
            return

    if selected_media_source is None:
        log.debug("Play Aborted, MediaSource was None")
        return

    source_id = selected_media_source.get("Id")
    seek_time = 0
    auto_resume = int(auto_resume)

    # process user data for resume points
    if auto_resume != -1:
        seek_time = (auto_resume / 1000) / 10000

    elif force_auto_resume:
        user_data = result.get("UserData")
        reasonable_ticks = int(user_data.get("PlaybackPositionTicks")) / 1000
        seek_time = reasonable_ticks / 10000

    else:
        user_data = result.get("UserData")
        if user_data.get("PlaybackPositionTicks") != 0:

            reasonable_ticks = int(user_data.get("PlaybackPositionTicks")) / 1000
            seek_time = reasonable_ticks / 10000
            display_time = str(timedelta(seconds=seek_time))

            resume_dialog = ResumeDialog("ResumeDialog.xml", addon_path, "default", "720p")
            resume_dialog.setResumeTime("Resume from " + display_time)
            resume_dialog.doModal()
            resume_result = resume_dialog.getResumeAction()
            del resume_dialog
            log.debug("Resume Dialog Result: {0}", resume_result)

            # check system settings for play action
            # if prompt is set ask to set it to auto resume
            # remove for now as the context dialog is now handeled in the monitor thread
            # params = {"setting": "myvideos.selectaction"}
            # setting_result = json_rpc('Settings.getSettingValue').execute(params)
            # log.debug("Current Setting (myvideos.selectaction): {0}", setting_result)
            # current_value = setting_result.get("result", None)
            # if current_value is not None:
            #     current_value = current_value.get("value", -1)
            # if current_value not in (2,3):
            #     return_value = xbmcgui.Dialog().yesno(string_load(30276), string_load(30277))
            #     if return_value:
            #         params = {"setting": "myvideos.selectaction", "value": 2}
            #         json_rpc_result = json_rpc('Settings.setSettingValue').execute(params)
            #         log.debug("Save Setting (myvideos.selectaction): {0}", json_rpc_result)

            if resume_result == 1:
                seek_time = 0
            elif resume_result == -1:
                return

    log.debug("play_session_id: {0}", play_session_id)
    playurl, playback_type, listitem_props = PlayUtils().get_play_url(selected_media_source, play_session_id)
    log.info("Play URL: {0} Playback Type: {1} ListItem Properties: {2}", playurl, playback_type, listitem_props)

    if playurl is None:
        return

    playback_type_string = "DirectPlay"
    if playback_type == "2":
        playback_type_string = "Transcode"
    elif playback_type == "1":
        playback_type_string = "DirectStream"

    # add the playback type into the overview
    if result.get("Overview", None) is not None:
        result["Overview"] = playback_type_string + "\n" + result.get("Overview")
    else:
        result["Overview"] = playback_type_string

    # add title decoration is needed
    item_title = result.get("Name", string_load(30280))

    # extract item info from result
    gui_options = {}
    gui_options["server"] = server
    gui_options["name_format"] = None
    gui_options["name_format_type"] = ""
    item_details = extract_item_info(result, gui_options)

    # create ListItem
    display_options = {}
    display_options["addCounts"] = False
    display_options["addResumePercent"] = False
    display_options["addSubtitleAvailable"] = False
    display_options["addUserRatings"] = False

    gui_item = add_gui_item("", item_details, display_options, False)
    list_item = gui_item[1]

    if playback_type == "2":  # if transcoding then prompt for audio and subtitle
        playurl = audio_subs_pref(playurl, list_item, selected_media_source, item_id, audio_stream_index,
                                  subtitle_stream_index)
        log.debug("New playurl for transcoding: {0}", playurl)

    elif playback_type == "1":  # for direct stream add any streamable subtitles
        external_subs(selected_media_source, list_item, item_id)

    # add playurl and data to the monitor
    data = {}
    data["item_id"] = item_id
    data["source_id"] = source_id
    data["playback_type"] = playback_type_string
    data["play_session_id"] = play_session_id
    data["play_action_type"] = "play"
    data["item_type"] = result.get("Type", None)
    data["can_delete"] = result.get("CanDelete", False)
    monitor.played_information[playurl] = data
    log.debug("Add to played_information: {0}", monitor.played_information)

    list_item.setPath(playurl)
    list_item = set_list_item_props(item_id, list_item, result, server, listitem_props, item_title)

    player = xbmc.Player()

    intro_items = []
    if play_cinema_intros and seek_time == 0:
        intro_items = get_playback_intros(item_id)

    if len(intro_items) > 0:
        playlist = play_all_files(intro_items, monitor, play_items=False)
        playlist.add(playurl, list_item)
    else:
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        playlist.add(playurl, list_item)

    player.play(playlist)

    if seek_time != 0:
        player.pause()
        monitor = xbmc.Monitor()
        count = 0
        while not player.isPlaying() and not monitor.abortRequested() and count != 100:
            count = count + 1
            xbmc.sleep(100)

        if count == 100 or not player.isPlaying() or monitor.abortRequested():
            log.info("PlaybackResumrAction : Playback item did not get to a play state in 10 seconds so exiting")
            player.stop()
            return

        log.info("PlaybackResumrAction : Playback is Running")

        seek_to_time = seek_time - jump_back_amount
        target_seek = (seek_to_time - 10)

        count = 0
        max_loops = 2 * 120
        while not monitor.abortRequested() and player.isPlaying() and count < max_loops:
            log.info("PlaybackResumrAction : Seeking to : {0}", seek_to_time)
            player.seekTime(seek_to_time)
            current_position = player.getTime()
            if current_position >= target_seek:
                break
            log.info("PlaybackResumrAction : target:{0} current:{1}", target_seek, current_position)
            count = count + 1
            xbmc.sleep(500)

        if count == max_loops:
            log.info("PlaybackResumrAction : Playback could not seek to required position")
            player.stop()
        else:
            count = 0
            while bool(xbmc.getCondVisibility("Player.Paused")) and count < 10:
                log.info("PlaybackResumrAction : Unpausing playback")
                player.pause()
                xbmc.sleep(1000)
                count = count + 1

            if count == 10:
                log.info("PlaybackResumrAction : Could not unpause")
            else:
                log.info("PlaybackResumrAction : Playback resumed")

    next_episode = get_next_episode(result)
    data["next_episode"] = next_episode
    send_next_episode_details(result, next_episode)


def __build_label2_from(source):
    videos = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Video"]
    audios = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Audio"]
    subtitles = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Subtitle"]

    details = [str(convert_size(source.get('Size', 0)))]
    # details.append(source.get('Container', ''))
    for video in videos:
        details.append('{} {} {}bit'.format(video.get('DisplayTitle', ''),
                                            video.get('VideoRange', ''),
                                            video.get('BitDepth', '')))
    aud = []
    for audio in audios:
        aud.append('{} {} {}'.format(audio.get('Language', ''),
                                     audio.get('Codec', ''),
                                     audio.get('Channels', '')))
    if len(aud) > 0:
        details.append(', '.join(aud).upper())
    subs = []
    for subtitle in subtitles:
        subs.append(subtitle.get('Language', ''))
    if len(subs) > 0:
        details.append('S: {}'.format(', '.join(subs)).upper())
    return ' | '.join(details)


def get_next_episode(item):
    if item.get("Type", "na") != "Episode":
        log.debug("Not an episode, can not get next")
        return None

    parent_id = item.get("ParentId", "na")
    item_index = item.get("IndexNumber", -1)

    if parent_id == "na":
        log.debug("No parent id, can not get next")
        return None

    if item_index == -1:
        log.debug("No episode number, can not get next")
        return None

    url = ('{server}/Users/{userid}/Items?' +
           '?Recursive=true' +
           '&ParentId=' + parent_id +
           '&IsVirtualUnaired=false' +
           '&IsMissing=False' +
           '&IncludeItemTypes=Episode' +
           '&ImageTypeLimit=1' +
           '&format=json')

    data_manager = DataManager()
    items_result = data_manager.get_content(url)
    log.debug("get_next_episode, sibling list: {0}", items_result)

    if items_result is None:
        log.debug("get_next_episode no results")
        return None

    item_list = items_result.get("Items", [])

    for item in item_list:
        index = item.get("IndexNumber", -1)
        # find the very next episode in the season
        if index == item_index + 1:
            log.debug("get_next_episode, found next episode: {0}", item)
            return item

    return None


def send_next_episode_details(item, next_episode):
    if next_episode is None:
        log.debug("No next episode")
        return

    gui_options = {}
    gui_options["server"] = download_utils.get_server()

    gui_options["name_format"] = None
    gui_options["name_format_type"] = ""

    item_details = extract_item_info(item, gui_options)
    next_item_details = extract_item_info(next_episode, gui_options)

    current_item = {}
    current_item["episodeid"] = item_details.id
    current_item["tvshowid"] = item_details.series_name
    current_item["title"] = item_details.name
    current_item["art"] = {}
    current_item["art"]["tvshow.poster"] = item_details.art.get('tvshow.poster', '')
    current_item["art"]["thumb"] = item_details.art.get('thumb', '')
    current_item["art"]["tvshow.fanart"] = item_details.art.get('tvshow.fanart', '')
    current_item["art"]["tvshow.landscape"] = item_details.art.get('tvshow.landscape', '')
    current_item["art"]["tvshow.clearart"] = item_details.art.get('tvshow.clearart', '')
    current_item["art"]["tvshow.clearlogo"] = item_details.art.get('tvshow.clearlogo', '')
    current_item["plot"] = item_details.plot
    current_item["showtitle"] = item_details.series_name
    current_item["playcount"] = item_details.play_count
    current_item["season"] = item_details.season_number
    current_item["episode"] = item_details.episode_number
    current_item["rating"] = item_details.critic_rating
    current_item["firstaired"] = item_details.year

    next_item = {}
    next_item["episodeid"] = next_item_details.id
    next_item["tvshowid"] = next_item_details.series_name
    next_item["title"] = next_item_details.name
    next_item["art"] = {}
    next_item["art"]["tvshow.poster"] = next_item_details.art.get('tvshow.poster', '')
    next_item["art"]["thumb"] = next_item_details.art.get('thumb', '')
    next_item["art"]["tvshow.fanart"] = next_item_details.art.get('tvshow.fanart', '')
    next_item["art"]["tvshow.landscape"] = next_item_details.art.get('tvshow.landscape', '')
    next_item["art"]["tvshow.clearart"] = next_item_details.art.get('tvshow.clearart', '')
    next_item["art"]["tvshow.clearlogo"] = next_item_details.art.get('tvshow.clearlogo', '')
    next_item["plot"] = next_item_details.plot
    next_item["showtitle"] = next_item_details.series_name
    next_item["playcount"] = next_item_details.play_count
    next_item["season"] = next_item_details.season_number
    next_item["episode"] = next_item_details.episode_number
    next_item["rating"] = next_item_details.critic_rating
    next_item["firstaired"] = next_item_details.year

    next_info = {
        "current_episode": current_item,
        "next_episode": next_item,
        "play_info": {
            "item_id": next_item_details.id,
            "auto_resume": False,
            "force_transcode": False
        }
    }
    send_event_notification("upnext_data", next_info)


def set_list_item_props(item_id, list_item, result, server, extra_props, title):
    # set up item and item info

    art = get_art(result, server=server)
    list_item.setIconImage(art['thumb'])  # back compat
    list_item.setProperty('fanart_image', art['fanart'])  # back compat
    list_item.setProperty('discart', art['discart'])  # not avail to setArt
    list_item.setArt(art)

    list_item.setProperty('IsPlayable', 'false')
    list_item.setProperty('IsFolder', 'false')
    list_item.setProperty('id', result.get("Id"))

    for prop in extra_props:
        list_item.setProperty(prop[0], prop[1])

    item_type = result.get("Type", "").lower()
    mediatype = 'video'

    if item_type == 'movie' or item_type == 'boxset':
        mediatype = 'movie'
    elif item_type == 'series':
        mediatype = 'tvshow'
    elif item_type == 'season':
        mediatype = 'season'
    elif item_type == 'episode':
        mediatype = 'episode'
    elif item_type == 'audio':
        mediatype = 'song'

    if item_type == "audio":

        details = {
            'title': title,
            'mediatype': mediatype
        }
        list_item.setInfo("Music", infoLabels=details)

    else:

        details = {
            'title': title,
            'plot': result.get("Overview"),
            'mediatype': mediatype
        }

        tv_show_name = result.get("SeriesName")
        if tv_show_name is not None:
            details['tvshowtitle'] = tv_show_name

        if item_type == "episode":
            episode_number = result.get("IndexNumber", -1)
            details["episode"] = str(episode_number)
            season_number = result.get("ParentIndexNumber", -1)
            details["season"] = str(season_number)
        elif item_type == "season":
            season_number = result.get("IndexNumber", -1)
            details["season"] = str(season_number)

        details["plotoutline"] = "jellyfin_id:%s" % (item_id,)

        list_item.setInfo("Video", infoLabels=details)

    return list_item


# For transcoding only
# Present the list of audio and subtitles to select from
# for external streamable subtitles add the URL to the Kodi item and let Kodi handle it
# else ask for the subtitles to be burnt in when transcoding
def audio_subs_pref(url, list_item, media_source, item_id, audio_stream_index, subtitle_stream_index):
    dialog = xbmcgui.Dialog()
    audio_streams_list = {}
    audio_streams = []
    subtitle_streams_list = {}
    subtitle_streams = ['No subtitles']
    downloadable_streams = []
    select_audio_index = audio_stream_index
    select_subs_index = subtitle_stream_index
    playurlprefs = ""
    default_audio = media_source.get('DefaultAudioStreamIndex', 1)
    default_sub = media_source.get('DefaultSubtitleStreamIndex', "")
    source_id = media_source["Id"]

    media_streams = media_source['MediaStreams']

    for stream in media_streams:
        # Since Jellyfin returns all possible tracks together, have to sort them.
        index = stream['Index']

        if 'Audio' in stream['Type']:
            codec = stream['Codec']
            channel_layout = stream.get('ChannelLayout', "")

            try:
                track = "%s - %s - %s %s" % (index, stream['Language'], codec, channel_layout)
            except:
                track = "%s - %s %s" % (index, codec, channel_layout)

            audio_streams_list[track] = index
            audio_streams.append(track)

        elif 'Subtitle' in stream['Type']:
            try:
                track = "%s - %s" % (index, stream['Language'])
            except:
                track = "%s - %s" % (index, stream['Codec'])

            default = stream['IsDefault']
            forced = stream['IsForced']
            downloadable = stream['IsTextSubtitleStream'] and stream['IsExternal'] and stream['SupportsExternalStream']

            if default:
                track = "%s - Default" % track
            if forced:
                track = "%s - Forced" % track
            if downloadable:
                downloadable_streams.append(index)

            subtitle_streams_list[track] = index
            subtitle_streams.append(track)

    # set audio index
    if select_audio_index is not None:
        playurlprefs += "&AudioStreamIndex=%s" % select_audio_index

    elif len(audio_streams) > 1:
        resp = dialog.select(string_load(30291), audio_streams)
        if resp > -1:
            # User selected audio
            selected = audio_streams[resp]
            select_audio_index = audio_streams_list[selected]
            playurlprefs += "&AudioStreamIndex=%s" % select_audio_index
        else:  # User backed out of selection
            playurlprefs += "&AudioStreamIndex=%s" % default_audio

    # set subtitle index
    if select_subs_index is not None:
        # Load subtitles in the listitem if downloadable
        if select_subs_index in downloadable_streams:
            subtitle_url = "%s/Videos/%s/%s/Subtitles/%s/Stream.srt"
            subtitle_url = subtitle_url % (download_utils.get_server(), item_id, source_id, select_subs_index)
            log.debug("Streaming subtitles url: {0} {1}", select_subs_index, subtitle_url)
            list_item.setSubtitles([subtitle_url])
        else:
            # Burn subtitles
            playurlprefs += "&SubtitleStreamIndex=%s" % select_subs_index

    elif len(subtitle_streams) > 1:
        resp = dialog.select(string_load(30292), subtitle_streams)
        if resp == 0:
            # User selected no subtitles
            pass
        elif resp > -1:
            # User selected subtitles
            selected = subtitle_streams[resp]
            select_subs_index = subtitle_streams_list[selected]

            # Load subtitles in the listitem if downloadable
            if select_subs_index in downloadable_streams:
                subtitle_url = "%s/Videos/%s/%s/Subtitles/%s/Stream.srt"
                subtitle_url = subtitle_url % (download_utils.get_server(), item_id, source_id, select_subs_index)
                log.debug("Streaming subtitles url: {0} {1}", select_subs_index, subtitle_url)
                list_item.setSubtitles([subtitle_url])
            else:
                # Burn subtitles
                playurlprefs += "&SubtitleStreamIndex=%s" % select_subs_index

        else:  # User backed out of selection
            playurlprefs += "&SubtitleStreamIndex=%s" % default_sub

    if url.find("|verifypeer=false") != -1:
        new_url = url.replace("|verifypeer=false", playurlprefs + "|verifypeer=false")
    else:
        new_url = url + playurlprefs

    return new_url


# direct stream, set any available subtitle streams
def external_subs(media_source, list_item, item_id):
    media_streams = media_source.get('MediaStreams')

    if media_streams is None:
        return

    externalsubs = []
    sub_names = []

    for stream in media_streams:

        if (stream['Type'] == "Subtitle"
                and stream['IsExternal']
                and stream['IsTextSubtitleStream']
                and stream['SupportsExternalStream']):

            index = stream['Index']
            source_id = media_source['Id']
            server = download_utils.get_server()
            token = download_utils.authenticate()

            if stream.get('DeliveryUrl', '').lower().startswith('/videos'):
                url = "%s%s" % (server, stream.get('DeliveryUrl'))
            else:
                url = ("%s/Videos/%s/%s/Subtitles/%s/Stream.%s?api_key=%s"
                       % (server, item_id, source_id, index, stream['Codec'], token))

            default = ""
            if stream['IsDefault']:
                default = "default"
            forced = ""
            if stream['IsForced']:
                forced = "forced"

            sub_name = stream.get('Language', "n/a") + " (" + stream.get('Codec', "n/a") + ") " + default + " " + forced

            sub_names.append(sub_name)
            externalsubs.append(url)

    if len(externalsubs) == 0:
        return

    settings = xbmcaddon.Addon()
    direct_stream_sub_select = settings.getSetting("direct_stream_sub_select")

    if direct_stream_sub_select == "0" or (len(externalsubs) == 1 and not direct_stream_sub_select == "2"):
        list_item.setSubtitles(externalsubs)
    else:
        resp = xbmcgui.Dialog().select(string_load(30292), sub_names)
        if resp > -1:
            selected_sub = externalsubs[resp]
            log.debug("External Subtitle Selected: {0}", selected_sub)
            list_item.setSubtitles([selected_sub])


def send_progress(monitor):
    play_data = get_playing_data(monitor.played_information)

    if play_data is None:
        return

    log.debug("Sending Progress Update")

    player = xbmc.Player()
    play_time = player.getTime()
    total_play_time = player.getTotalTime()
    play_data["currentPossition"] = play_time
    play_data["duration"] = total_play_time
    play_data["currently_playing"] = True

    item_id = play_data.get("item_id")
    if item_id is None:
        return

    source_id = play_data.get("source_id")

    ticks = int(play_time * 10000000)
    duration = int(total_play_time * 10000000)
    paused = play_data.get("paused", False)
    playback_type = play_data.get("playback_type")
    play_session_id = play_data.get("play_session_id")

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist_position = playlist.getposition()
    playlist_size = playlist.size()

    volume, muted = get_volume()

    postdata = {
        'QueueableMediaTypes': "Video",
        'CanSeek': True,
        'ItemId': item_id,
        'MediaSourceId': source_id,
        'PositionTicks': ticks,
        'RunTimeTicks': duration,
        'IsPaused': paused,
        'IsMuted': muted,
        'PlayMethod': playback_type,
        'PlaySessionId': play_session_id,
        'PlaylistIndex': playlist_position,
        'PlaylistLength': playlist_size,
        'VolumeLevel': volume
    }

    log.debug("Sending POST progress started: {0}", postdata)

    url = "{server}/Sessions/Playing/Progress"
    download_utils.download_url(url, post_body=postdata, method="POST")


def get_volume():
    json_data = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume", "muted"]}, "id": 1 }')
    result = json.loads(json_data)
    result = result.get('result', {})
    volume = result.get('volume')
    muted = result.get('muted')

    return volume, muted


def prompt_for_stop_actions(item_id, data):
    log.debug("prompt_for_stop_actions Called : {0}", data)

    settings = xbmcaddon.Addon()
    current_position = data.get("currentPossition", 0)
    duration = data.get("duration", 0)
    # media_source_id = data.get("source_id")
    next_episode = data.get("next_episode")
    item_type = data.get("item_type")
    can_delete = data.get("can_delete", False)

    prompt_next_percentage = int(settings.getSetting('promptPlayNextEpisodePercentage'))
    play_prompt = settings.getSetting('promptPlayNextEpisodePercentage_prompt') == "true"
    prompt_delete_episode_percentage = int(settings.getSetting('promptDeleteEpisodePercentage'))
    prompt_delete_movie_percentage = int(settings.getSetting('promptDeleteMoviePercentage'))

    # everything is off so return
    if (prompt_next_percentage == 100 and
            prompt_delete_episode_percentage == 100 and
            prompt_delete_movie_percentage == 100):
        return

    prompt_to_delete = False

    # if no runtime we cant calculate perceantge so just return
    if duration == 0:
        log.debug("No duration so returing")
        return

    # item percentage complete
    # percenatge_complete = int(((current_position * 10000000) / runtime) * 100)
    percenatge_complete = int((current_position / duration) * 100)
    log.debug("Episode Percentage Complete: {0}", percenatge_complete)

    if (can_delete and
            prompt_delete_episode_percentage < 100 and
            item_type == "Episode" and
            percenatge_complete > prompt_delete_episode_percentage):
        prompt_to_delete = True

    if (can_delete and
            prompt_delete_movie_percentage < 100 and
            item_type == "Movie" and
            percenatge_complete > prompt_delete_movie_percentage):
        prompt_to_delete = True

    if prompt_to_delete:
        log.debug("Prompting for delete")
        delete(item_id)

    # prompt for next episode
    if (next_episode is not None and
            prompt_next_percentage < 100 and
            item_type == "Episode" and
            percenatge_complete > prompt_next_percentage):

        # resp = True
        index = next_episode.get("IndexNumber", -1)
        if play_prompt:
            # series_name = next_episode.get("SeriesName")
            # next_epp_name = "Episode %02d - (%s)" % (index, next_episode.get("Name", "n/a"))

            plugin_path = settings.getAddonInfo('path')
            plugin_path_real = xbmc.translatePath(os.path.join(plugin_path))

            play_next_dialog = PlayNextDialog("PlayNextDialog.xml", plugin_path_real, "default", "720p")
            play_next_dialog.set_episode_info(next_episode)
            play_next_dialog.doModal()

            if not play_next_dialog.get_play_called():
                xbmc.executebuiltin("Container.Refresh")

            # resp = xbmcgui.Dialog().yesno(string_load(30283),
            #                              series_name,
            #                              next_epp_name,
            #                              autoclose=20000)
        """
        if resp:
            next_item_id = next_episode.get("Id")
            log.debug("Playing Next Episode: {0}", next_item_id)

            play_info = {}
            play_info["item_id"] = next_item_id
            play_info["auto_resume"] = "-1"
            play_info["force_transcode"] = False
            send_event_notification("jellycon_play_action", play_info)

        else:
            xbmc.executebuiltin("Container.Refresh")
        """


def stop_all_playback(played_information):
    log.debug("stop_all_playback : {0}", played_information)

    if len(played_information) == 0:
        return

    log.debug("played_information: {0}", played_information)

    home_screen = HomeWindow()
    home_screen.clear_property("currently_playing_id")

    for item_url in played_information:
        data = played_information.get(item_url)
        if data.get("currently_playing", False) is True:
            log.debug("item_url: {0}", item_url)
            log.debug("item_data: {0}", data)

            current_position = data.get("currentPossition", 0)
            duration = data.get("duration", 0)
            jellyfin_item_id = data.get("item_id")
            jellyfin_source_id = data.get("source_id")
            play_session_id = data.get("play_session_id")

            if jellyfin_item_id is not None and current_position >= 0:
                log.debug("Playback Stopped at: {0}", current_position)

                url = "{server}/Sessions/Playing/Stopped"
                postdata = {
                    'ItemId': jellyfin_item_id,
                    'MediaSourceId': jellyfin_source_id,
                    'PositionTicks': int(current_position * 10000000),
                    'RunTimeTicks': int(duration * 10000000),
                    'PlaySessionId': play_session_id
                }
                download_utils.download_url(url, post_body=postdata, method="POST")
                data["currently_playing"] = False

                if data.get("play_action_type", "") == "play":
                    prompt_for_stop_actions(jellyfin_item_id, data)

    device_id = ClientInformation().get_device_id()
    url = "{server}/Videos/ActiveEncodings?DeviceId=%s" % device_id
    download_utils.download_url(url, method="DELETE")


def get_playing_data(play_data_map):
    try:
        playing_file = xbmc.Player().getPlayingFile()
    except Exception as e:
        log.error("get_playing_data : getPlayingFile() : {0}", e)
        return None
    log.debug("get_playing_data : getPlayingFile() : {0}", playing_file)
    if playing_file not in play_data_map:
        infolabel_path_and_file = xbmc.getInfoLabel("Player.Filenameandpath")
        log.debug("get_playing_data : Filenameandpath : {0}", infolabel_path_and_file)
        if infolabel_path_and_file not in play_data_map:
            log.debug("get_playing_data : play data not found")
            return None
        else:
            playing_file = infolabel_path_and_file

    return play_data_map.get(playing_file)


class Service(xbmc.Player):

    def __init__(self, *args):
        log.debug("Starting monitor service: {0}", args)
        self.played_information = {}

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        stop_all_playback(self.played_information)

        if not xbmc.Player().isPlaying():
            log.debug("onPlayBackStarted: not playing file!")
            return

        play_data = get_playing_data(self.played_information)

        if play_data is None:
            return

        play_data["paused"] = False
        play_data["currently_playing"] = True

        jellyfin_item_id = play_data["item_id"]
        jellyfin_source_id = play_data["source_id"]
        playback_type = play_data["playback_type"]
        play_session_id = play_data["play_session_id"]

        # if we could not find the ID of the current item then return
        if jellyfin_item_id is None:
            return

        log.debug("Sending Playback Started")
        postdata = {
            'QueueableMediaTypes': "Video",
            'CanSeek': True,
            'ItemId': jellyfin_item_id,
            'MediaSourceId': jellyfin_source_id,
            'PlayMethod': playback_type,
            'PlaySessionId': play_session_id
        }

        log.debug("Sending POST play started: {0}", postdata)

        url = "{server}/Sessions/Playing"
        download_utils.download_url(url, post_body=postdata, method="POST")

        home_screen = HomeWindow()
        home_screen.set_property("currently_playing_id", str(jellyfin_item_id))

    def onPlayBackEnded(self):
        # Will be called when kodi stops playing a file
        log.debug("onPlayBackEnded")
        stop_all_playback(self.played_information)

    def onPlayBackStopped(self):
        # Will be called when user stops kodi playing a file
        log.debug("onPlayBackStopped")
        stop_all_playback(self.played_information)

    def onPlayBackPaused(self):
        # Will be called when kodi pauses the video
        log.debug("onPlayBackPaused")

        play_data = get_playing_data(self.played_information)

        if play_data is not None:
            play_data['paused'] = True
            send_progress(self)

    def onPlayBackResumed(self):
        # Will be called when kodi resumes the video
        log.debug("onPlayBackResumed")

        play_data = get_playing_data(self.played_information)

        if play_data is not None:
            play_data['paused'] = False
            send_progress(self)

    def onPlayBackSeek(self, time, seek_offset):
        # Will be called when kodi seeks in video
        log.debug("onPlayBackSeek")
        send_progress(self)


class PlaybackService(xbmc.Monitor):
    background_image_cache_thread = None

    def __init__(self, monitor):
        self.monitor = monitor

    def onNotification(self, sender, method, data):
        log.debug("PlaybackService:onNotification:{0}:{1}:{2}", sender, method, data)

        if method == 'GUI.OnScreensaverActivated':
            self.screensaver_activated()
            return

        if method == 'GUI.OnScreensaverDeactivated':
            self.screensaver_deactivated()
            return

        if sender[-7:] != '.SIGNAL':
            return

        signal = method.split('.', 1)[-1]
        if signal not in ("jellycon_play_action", "jellycon_play_youtube_trailer_action", "set_view"):
            return

        data_json = json.loads(data)
        message_data = data_json[0]
        log.debug("PlaybackService:onNotification:{0}", message_data)
        decoded_data = base64.b64decode(message_data)
        play_info = json.loads(decoded_data)

        if signal == "jellycon_play_action":
            log.info("Received jellycon_play_action : {0}", play_info)
            play_file(play_info, self.monitor)
        elif signal == "jellycon_play_youtube_trailer_action":
            log.info("Received jellycon_play_trailer_action : {0}", play_info)
            trailer_link = play_info["url"]
            xbmc.executebuiltin(trailer_link)
        elif signal == "set_view":
            view_id = play_info["view_id"]
            log.debug("Setting view id: {0}", view_id)
            xbmc.executebuiltin("Container.SetViewMode(%s)" % int(view_id))

    def screensaver_activated(self):
        log.debug("Screen Saver Activated")

        home_screen = HomeWindow()
        home_screen.clear_property("skip_select_user")

        settings = xbmcaddon.Addon()
        stop_playback = settings.getSetting("stopPlaybackOnScreensaver") == 'true'

        if stop_playback:
            player = xbmc.Player()
            if player.isPlayingVideo():
                log.debug("Screen Saver Activated : isPlayingVideo() = true")
                play_data = get_playing_data(self.monitor.played_information)
                if play_data:
                    log.debug("Screen Saver Activated : this is an JellyCon item so stop it")
                    player.stop()

        # xbmc.executebuiltin("Dialog.Close(selectdialog, true)")

        clear_old_cache_data()

        cache_images = settings.getSetting('cacheImagesOnScreenSaver') == 'true'
        if cache_images:
            self.background_image_cache_thread = CacheArtwork()
            self.background_image_cache_thread.start()

    def screensaver_deactivated(self):
        log.debug("Screen Saver Deactivated")

        if self.background_image_cache_thread:
            self.background_image_cache_thread.stop_activity()
            self.background_image_cache_thread = None

        settings = xbmcaddon.Addon()
        show_change_user = settings.getSetting('changeUserOnScreenSaver') == 'true'
        if show_change_user:
            home_screen = HomeWindow()
            skip_select_user = home_screen.get_property("skip_select_user")
            if skip_select_user is not None and skip_select_user == "true":
                return
            xbmc.executebuiltin("RunScript(plugin.video.jellycon,0,?mode=CHANGE_USER)")
