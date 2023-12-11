from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import json
import os
import re
import sys
import binascii
from datetime import timedelta

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import xbmcplugin
from six.moves.urllib.parse import urlencode

from .jellyfin import api
from .lazylogger import LazyLogger
from .dialogs import ResumeDialog
from .utils import send_event_notification, convert_size, get_device_id, translate_string, load_user_details, translate_path, get_jellyfin_url, download_external_sub, get_bitrate
from .kodi_utils import HomeWindow
from .datamanager import clear_old_cache_data
from .item_functions import extract_item_info, add_gui_item, get_art
from .cache_images import CacheArtwork
from .picture_viewer import PictureViewer
from .tracking import timer
from .playnext import PlayNextDialog

log = LazyLogger(__name__)
settings = xbmcaddon.Addon()


def play_all_files(items, play_items=True):
    home_window = HomeWindow()
    log.debug("playAllFiles called with items: {0}", items)
    server = settings.getSetting('server_address')

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    playlist_data = {}

    for item in items:

        item_id = item.get("Id")

        # get playback info
        playback_info = get_item_playback_info(item_id, False)
        if playback_info is None:
            log.debug("playback_info was None, could not get MediaSources so can not play!")
            return
        if playback_info.get("ErrorCode") is not None:
            error_string = playback_info.get("ErrorCode")
            xbmcgui.Dialog().notification(translate_string(30316),
                                          error_string,
                                          icon="special://home/addons/plugin.video.jellycon/icon.png")
            return

        play_session_id = playback_info.get("PlaySessionId")

        # select the media source to use
        sources = playback_info.get('MediaSources')

        selected_media_source = sources[0]
        source_id = selected_media_source.get("Id")

        playurl, playback_type, listitem_props = get_play_url(selected_media_source, play_session_id)
        log.info("Play URL: {0} PlaybackType: {1} ListItem Properties: {2}".format(playurl, playback_type, listitem_props))

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
        item_title = item.get("Name", translate_string(30280))
        list_item = xbmcgui.ListItem(label=item_title)

        # add playurl and data to the monitor
        playlist_data[playurl] = {}
        playlist_data[playurl]["item_id"] = item_id
        playlist_data[playurl]["source_id"] = source_id
        playlist_data[playurl]["playback_type"] = playback_type_string
        playlist_data[playurl]["play_session_id"] = play_session_id
        playlist_data[playurl]["play_action_type"] = "play_all"
        home_window.set_property('playlist', json.dumps(playlist_data))

        # Set now_playing to the first track
        if len(playlist_data) == 1:
            home_window.set_property('now_playing', json.dumps(playlist_data[playurl]))

        list_item.setPath(playurl)
        list_item = set_list_item_props(item_id, list_item, item, server, listitem_props, item_title)

        playlist.add(playurl, list_item)
        if play_items and playlist.size() == 1:
            # Play the first item immediately before processing the rest
            xbmc.Player().play(playlist)

    if play_items:
        # Should already be playing, don't need to return anything
        return None
    else:
        return playlist


def play_list_of_items(id_list):
    log.debug("Loading  all items in the list")
    items = []

    for item_id in id_list:
        url = "/Users/{}/Items/{}?format=json".format(api.user_id, item_id)
        result = api.get(url)
        if result is None:
            log.debug("Playfile item was None, so can not play!")
            return
        items.append(result)

    return play_all_files(items)


def add_to_playlist(play_info):
    log.debug("Adding item to playlist : {0}".format(play_info))

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    server = settings.getSetting('server_address')

    item_id = play_info.get("item_id")

    url = "/Users/{}/Items/{}?format=json".format(api.user_id, item_id)
    item = api.get(url)
    if item is None:
        log.debug("Playfile item was None, so can not play!")
        return

    # get playback info
    playback_info = get_item_playback_info(item_id, False)
    if playback_info is None:
        log.debug("playback_info was None, could not get MediaSources so can not play!")
        return
    if playback_info.get("ErrorCode") is not None:
        error_string = playback_info.get("ErrorCode")
        xbmcgui.Dialog().notification(translate_string(30316),
                                      error_string,
                                      icon="special://home/addons/plugin.video.jellycon/icon.png")
        return

    play_session_id = playback_info.get("PlaySessionId")

    # select the media source to use
    sources = playback_info.get('MediaSources')

    selected_media_source = sources[0]
    source_id = selected_media_source.get("Id")

    playurl, playback_type, listitem_props = get_play_url(selected_media_source, play_session_id)
    log.info("Play URL: {0} PlaybackType: {1} ListItem Properties: {2}".format(playurl, playback_type, listitem_props))

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
    item_title = item.get("Name", translate_string(30280))
    list_item = xbmcgui.ListItem(label=item_title)

    # add playurl and data to the monitor
    data = {}
    data["item_id"] = item_id
    data["source_id"] = source_id
    data["playback_type"] = playback_type_string
    data["play_session_id"] = play_session_id
    data["play_action_type"] = "play_all"

    list_item.setPath(playurl)
    list_item = set_list_item_props(item_id, list_item, item, server, listitem_props, item_title)

    playlist.add(playurl, list_item)


def get_playback_intros(item_id):
    log.debug("get_playback_intros")
    url = "/Users/{}/Items/{}/Intros".format(api.user_id, item_id)
    intro_items = api.get(url)

    if intro_items is None:
        log.debug("get_playback_intros failed!")
        return

    into_list = []
    intro_items = intro_items["Items"]
    for into in intro_items:
        into_list.append(into)

    return into_list


@timer
def play_file(play_info):
    item_id = play_info.get("item_id")

    channel_id = None
    home_window = HomeWindow()
    last_url = home_window.get_property("last_content_url")
    if last_url:
        home_window.set_property("skip_cache_for_" + last_url, "true")

    action = play_info.get("action", "play")
    if action == "add_to_playlist":
        add_to_playlist(play_info)
        return

    # if this is a list of items them add them all to the play list
    if isinstance(item_id, list):
        return play_list_of_items(item_id)

    auto_resume = play_info.get("auto_resume", "-1")
    force_transcode = play_info.get("force_transcode", False)
    media_source_id = play_info.get("media_source_id", "")
    subtitle_stream_index = play_info.get("subtitle_stream_index", None)
    audio_stream_index = play_info.get("audio_stream_index", None)

    log.debug("playFile id({0}) resume({1}) force_transcode({2})".format(item_id, auto_resume, force_transcode))

    addon_path = settings.getAddonInfo('path')
    force_auto_resume = settings.getSetting('forceAutoResume') == 'true'
    jump_back_amount = int(settings.getSetting("jump_back_amount"))
    play_cinema_intros = settings.getSetting('play_cinema_intros') == 'true'

    server = settings.getSetting('server_address')

    url = "/Users/{}/Items/{}?format=json".format(api.user_id, item_id)
    result = api.get(url)
    log.debug("Playfile item: {0}".format(result))

    if result is None:
        log.debug("Playfile item was None, so can not play!")
        return

    # Generate an instant mix based on the item
    if action == 'instant_mix':
        max_queue = int(settings.getSetting('max_play_queue'))
        url_root = '/Items/{}/InstantMix'.format(item_id)
        url_params = {
            'UserId': api.user_id,
            'Fields': 'MediaSources',
            'IncludeItemTypes': 'Audio',
            'SortBy': 'SortName',
            'limit': max_queue
        }
        url = get_jellyfin_url(url_root, url_params)
        result = api.get(url)
        log.debug("PlayAllFiles items: {0}".format(result))

        # process each item
        items = result["Items"]
        if items is None:
            items = []
        return play_all_files(items)

    '''
    if this is a season, playlist, artist, album, or a full library then play
    *all* items in that parent.
    * Taking the max queue size setting into account
    '''
    if result.get("Type") in ["Season", "Series", "MusicArtist", "MusicAlbum",
                              "Playlist", "CollectionFolder", "MusicGenre"]:
        max_queue = int(settings.getSetting('max_play_queue'))
        log.debug("PlayAllFiles for parent item id: {0}".format(item_id))
        url_root = '/Users/{}/Items'.format(api.user_id)
        # Look specifically for episodes or audio files
        url_params = {
            'Fields': 'MediaSources',
            'IncludeItemTypes': 'Episode,Audio',
            'Recursive': True,
            'SortBy': 'SortName',
            'limit': max_queue
        }
        if result.get("Type") == "MusicGenre":
            url_params['genreIds'] = item_id
        else:
            url_params['ParentId'] = item_id

        if action == 'shuffle':
            url_params['SortBy'] = 'Random'

        url = get_jellyfin_url(url_root, url_params)
        result = api.get(url)
        log.debug("PlayAllFiles items: {0}".format(result))

        # process each item
        items = result["Items"]
        if items is None:
            items = []
        return play_all_files(items)

    # if this is a program from live tv epg then play the actual channel
    if result.get("Type") == "Program":
        channel_id = result.get("ChannelId")
        url = "/Users/{}/Items/{}?format=json".format(api.user_id, channel_id)
        result = api.get(url)
        item_id = result["Id"]
    elif result.get('Type') == "TvChannel":
        channel_id = result.get("Id")
        url = "/Users/{}/Items/{}?format=json".format(api.user_id, channel_id)
        result = api.get(url)
        item_id = result["Id"]
    elif result.get("Type") == "Photo":
        play_url = "%s/Items/%s/Images/Primary"
        play_url = play_url % (server, item_id)

        plugin_path = translate_path(os.path.join(xbmcaddon.Addon().getAddonInfo('path')))
        action_menu = PictureViewer("PictureViewer.xml", plugin_path, "default", "720p")
        action_menu.setPicture(play_url)
        action_menu.doModal()
        return

    # get playback info from the server using the device profile
    playback_info = get_item_playback_info(item_id, force_transcode)
    if playback_info is None:
        log.debug("playback_info was None, could not get MediaSources so can not play!")
        return
    if playback_info.get("ErrorCode") is not None:
        error_string = playback_info.get("ErrorCode")
        xbmcgui.Dialog().notification(translate_string(30316),
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
        resp = dialog.select(translate_string(30309), items, useDetails=True)
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
            log.debug("Resume Dialog Result: {0}".format(resume_result))

            if resume_result == 1:
                seek_time = 0
            elif resume_result == -1:
                return

    log.debug("play_session_id: {0}".format(play_session_id))
    playurl, playback_type, listitem_props = get_play_url(selected_media_source, play_session_id, channel_id)
    log.info("Play URL: {0} Playback Type: {1} ListItem Properties: {2}".format(playurl, playback_type, listitem_props))

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
    item_title = result.get("Name", translate_string(30280))

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

    gui_item = add_gui_item(item_id, item_details, display_options, False)
    list_item = gui_item[1]

    if playback_type == "2":  # if transcoding then prompt for audio and subtitle
        playurl = audio_subs_pref(playurl, list_item, selected_media_source, item_id, audio_stream_index,
                                  subtitle_stream_index)
        log.debug("New playurl for transcoding: {0}".format(playurl))

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

    # Check for next episodes
    if result.get('Type') == 'Episode':
        next_episode = get_next_episode(result)
        data["next_episode"] = next_episode
        send_next_episode_details(result, next_episode)

    # We need the livestream id to properly delete encodings
    if result.get("Type", "") in ["Program", "TvChannel"]:
        for media_source in media_sources:
            livestream_id = media_source.get("LiveStreamId")
            data["livestream_id"] = livestream_id
            if livestream_id:
                break

    home_window.set_property('now_playing', json.dumps(data))

    list_item.setPath(playurl)
    list_item = set_list_item_props(item_id, list_item, result, server, listitem_props, item_title)

    player = xbmc.Player()

    intro_items = []
    if play_cinema_intros and seek_time == 0:
        intro_items = get_playback_intros(item_id)

    if len(intro_items) > 0:
        playlist = play_all_files(intro_items, play_items=False)
        playlist.add(playurl, list_item)
        player.play(playlist)
    else:
        if len(sys.argv) > 1 and int(sys.argv[1]) > 0:
            # Play from info menu
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, list_item)
        else:
            '''
            Play from remote control or addon menus.  Doesn't have a handle,
            so need to call player directly
            '''
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
            log.info("PlaybackResumrAction : Seeking to : {0}".format(seek_to_time))
            player.seekTime(seek_to_time)
            current_position = player.getTime()
            if current_position >= target_seek:
                break
            log.info("PlaybackResumrAction : target:{0} current:{1}".format(target_seek, current_position))
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


def __build_label2_from(source):
    videos = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Video"]
    audios = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Audio"]
    subtitles = [item for item in source.get('MediaStreams', {}) if item.get('Type') == "Subtitle"]

    details = [str(convert_size(source.get('Size', 0)))]
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
    if item.get("Type") != "Episode":
        log.debug("Not an episode, can not get next")
        return None

    parent_id = item.get("ParentId")
    item_index = item.get("IndexNumber")

    if parent_id is None:
        log.debug("No parent id, can not get next")
        return None

    if item_index is None:
        log.debug("No episode number, can not get next")
        return None

    url = ('/Users/{}/Items?'.format(api.user_id) +
           '?Recursive=true' +
           '&ParentId=' + parent_id +
           '&IsVirtualUnaired=false' +
           '&IsMissing=False' +
           '&IncludeItemTypes=Episode' +
           '&ImageTypeLimit=1' +
           '&format=json')

    items_result = api.get(url)
    log.debug("get_next_episode, sibling list: {0}".format(items_result))

    if items_result is None:
        log.debug("get_next_episode no results")
        return None

    item_list = items_result.get("Items") or []

    for item in item_list:
        # find the very next episode in the season
        if item.get("IndexNumber") == item_index + 1:
            log.debug("get_next_episode, found next episode: {0}".format(item))
            return item

    return None


def send_next_episode_details(item, next_episode):
    if next_episode is None:
        log.debug("No next episode")
        return

    gui_options = {}
    gui_options["server"] = settings.getSetting('server_address')

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
    send_event_notification("upnext_data", next_info, True)


def set_list_item_props(item_id, list_item, result, server, extra_props, title):
    # set up item and item info

    art = get_art(result, server=server)
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
            codec = stream.get('Codec', None)
            channel_layout = stream.get('ChannelLayout', "")

            if not codec:
                # Probably tvheadend and has no other info
                track = "%s - default" % (index)
            else:
                try:
                    # Track includes language
                    track = "%s - %s - %s %s" % (index, stream['Language'], codec, channel_layout)
                except KeyError:
                    # Track doesn't include language
                    track = "%s - %s %s" % (index, codec, channel_layout)

            audio_streams_list[track] = index
            audio_streams.append(track)

        elif 'Subtitle' in stream['Type']:
            try:
                # Track includes language
                track = "%s - %s" % (index, stream['Language'])
            except KeyError:
                # Track doesn't include language
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
        resp = dialog.select(translate_string(30291), audio_streams)
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
            subtitle_url = subtitle_url % (settings.getSetting('server_address'), item_id, source_id, select_subs_index)
            log.debug("Streaming subtitles url: {0} {1}".format(select_subs_index, subtitle_url))
            list_item.setSubtitles([subtitle_url])
        else:
            # Burn subtitles
            playurlprefs += "&SubtitleStreamIndex=%s" % select_subs_index

    elif len(subtitle_streams) > 1:
        resp = dialog.select(translate_string(30292), subtitle_streams)
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
                subtitle_url = subtitle_url % (settings.getSetting('server_address'), item_id, source_id, select_subs_index)
                log.debug("Streaming subtitles url: {0} {1}".format(select_subs_index, subtitle_url))
                list_item.setSubtitles([subtitle_url])
            else:
                # Burn subtitles
                playurlprefs += "&SubtitleStreamIndex=%s" % select_subs_index

        else:  # User backed out of selection
            playurlprefs += "&SubtitleStreamIndex=%s" % default_sub

    new_url = url + playurlprefs

    return new_url


# direct stream, set any available subtitle streams
def external_subs(media_source, list_item, item_id):
    media_streams = media_source.get('MediaStreams')

    if media_streams is None:
        return

    externalsubs = []
    sub_names = []

    server = settings.getSetting('server_address')

    for stream in media_streams:

        if (stream['Type'] == "Subtitle"
                and stream['IsExternal']
                and stream['IsTextSubtitleStream']
                and stream['SupportsExternalStream']):

            language = stream.get('Language', '')
            if language and stream['IsDefault']:
                language = '{}.default'.format(language)
            if language and stream['IsForced']:
                language = '{}.forced'.format(language)
            is_sdh = stream.get('Title') and stream['Title'] in ('sdh', 'cc')
            if language and is_sdh:
                language = '{}.{}'.format(language, stream['Title'])
            codec = stream.get('Codec', '')

            url = '{}{}'.format(server, stream.get('DeliveryUrl'))
            if language:
                '''
                Starting in 10.8, the server no longer provides language
                specific download points.  We have to download the file
                and name it with the language code ourselves so Kodi
                will parse it correctly
                '''
                subtitle_file = download_external_sub(language, codec, url)
            else:
                # If there is no language defined, we can go directly to the server
                subtitle_file = url

            sub_name = '{} ( {} )'.format(language, codec)

            sub_names.append(sub_name)
            externalsubs.append(subtitle_file)

    if len(externalsubs) == 0:
        return

    direct_stream_sub_select = settings.getSetting("direct_stream_sub_select")

    if direct_stream_sub_select == "0" or (len(externalsubs) == 1 and not direct_stream_sub_select == "2"):
        list_item.setSubtitles(externalsubs)
    else:
        resp = xbmcgui.Dialog().select(translate_string(30292), sub_names)
        if resp > -1:
            selected_sub = externalsubs[resp]
            log.debug("External Subtitle Selected: {0}".format(selected_sub))
            list_item.setSubtitles([selected_sub])


def send_progress():
    home_window = HomeWindow()
    play_data = get_playing_data()

    if play_data is None:
        return

    log.debug("Sending Progress Update")

    player = xbmc.Player()
    item_id = play_data.get("item_id")

    if item_id is None:
        return

    play_time = player.getTime()
    total_play_time = player.getTotalTime()
    play_data["current_position"] = play_time
    play_data["duration"] = total_play_time
    play_data["currently_playing"] = True

    home_window.set_property('now_playing', json.dumps(play_data))

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

    log.debug("Sending POST progress started: {0}".format(postdata))

    url = "/Sessions/Playing/Progress"
    api.post(url, postdata)


def get_volume():
    json_data = xbmc.executeJSONRPC(
        '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["volume", "muted"]}, "id": 1 }')
    result = json.loads(json_data)
    result = result.get('result', {})
    volume = result.get('volume')
    muted = result.get('muted')

    return volume, muted


def prompt_for_stop_actions(item_id, data):
    log.debug("prompt_for_stop_actions Called : {0}".format(data))

    current_position = data.get("current_position", 0)
    duration = data.get("duration", 0)
    next_episode = data.get("next_episode")
    item_type = data.get("item_type")

    prompt_next_percentage = int(settings.getSetting('promptPlayNextEpisodePercentage'))
    play_prompt = settings.getSetting('promptPlayNextEpisodePercentage_prompt') == "true"
    prompt_delete_episode_percentage = int(settings.getSetting('promptDeleteEpisodePercentage'))
    prompt_delete_movie_percentage = int(settings.getSetting('promptDeleteMoviePercentage'))

    # everything is off so return
    if (prompt_next_percentage == 100 and
            prompt_delete_episode_percentage == 100 and
            prompt_delete_movie_percentage == 100):
        return

    # if no runtime we can't calculate perceantge so just return
    if duration == 0:
        log.debug("No duration so returning")
        return

    # item percentage complete
    percentage_complete = int((current_position / duration) * 100)
    log.debug("Episode Percentage Complete: {0}".format(percentage_complete))

    # prompt for next episode
    if (next_episode is not None and
            prompt_next_percentage < 100 and
            item_type == "Episode" and
            percentage_complete > prompt_next_percentage):

        if play_prompt:

            plugin_path = settings.getAddonInfo('path')
            plugin_path_real = translate_path(os.path.join(plugin_path))

            play_next_dialog = PlayNextDialog("PlayNextDialog.xml", plugin_path_real, "default", "720p")
            play_next_dialog.set_episode_info(next_episode)
            play_next_dialog.doModal()

            if not play_next_dialog.get_play_called():
                xbmc.executebuiltin("Container.Refresh")


def stop_all_playback():

    home_window = HomeWindow()
    played_information_string = home_window.get_property('played_information')
    if played_information_string:
        played_information = json.loads(played_information_string)
    else:
        played_information = {}

    log.debug("stop_all_playback : {0}".format(played_information))

    if len(played_information) == 0:
        return

    log.debug("played_information: {0}".format(played_information))
    clear_entries = []

    home_window.clear_property("currently_playing_id")

    for item in played_information:
        data = played_information.get(item)
        if data.get("currently_playing", False) is True:
            log.debug("item_data: {0}".format(data))

            current_position = data.get("current_position", 0)
            duration = data.get("duration", 0)
            jellyfin_item_id = data.get("item_id")
            jellyfin_source_id = data.get("source_id")
            play_session_id = data.get("play_session_id")
            livestream_id = data.get('livestream_id')

            if jellyfin_item_id is not None and current_position >= 0:
                log.debug("Playback Stopped at: {0}".format(current_position))

                url = "/Sessions/Playing/Stopped"
                postdata = {
                    'ItemId': jellyfin_item_id,
                    'MediaSourceId': jellyfin_source_id,
                    'PositionTicks': int(current_position * 10000000),
                    'RunTimeTicks': int(duration * 10000000),
                    'PlaySessionId': play_session_id
                }

                # If this is a livestream, include the id in the stopped call
                if livestream_id:
                    postdata['LiveStreamId'] = livestream_id

                api.post(url, postdata)
                data["currently_playing"] = False

                if data.get("play_action_type", "") == "play":
                    prompt_for_stop_actions(jellyfin_item_id, data)

                clear_entries.append(item)

            if data.get('playback_type') == 'Transcode':
                device_id = get_device_id()
                url = "/Videos/ActiveEncodings?DeviceId=%s&playSessionId=%s" % (device_id, play_session_id)
                api.delete(url)

    for entry in clear_entries:
        del played_information[entry]

    home_window.set_property('played_information', json.dumps(played_information))


def get_playing_data():
    player = xbmc.Player()
    home_window = HomeWindow()
    play_data_string = home_window.get_property('now_playing')
    try:
        play_data = json.loads(play_data_string)
    except ValueError:
        # This isn't a JellyCon item
        return None

    played_information_string = home_window.get_property('played_information')
    if played_information_string:
        played_information = json.loads(played_information_string)
    else:
        played_information = {}

    playlist_data_string = home_window.get_property('playlist')
    if playlist_data_string:
        playlist_data = json.loads(playlist_data_string)
    else:
        playlist_data = {}

    item_id = play_data.get("item_id")

    server = settings.getSetting('server_address')
    try:
        playing_file = player.getPlayingFile()
    except Exception as e:
        log.error("get_playing_data : getPlayingFile() : {0}".format(e))
        return None
    log.debug("get_playing_data : getPlayingFile() : {0}".format(playing_file))
    if server in playing_file and item_id is not None:
        play_time = player.getTime()
        total_play_time = player.getTotalTime()

        if item_id is not None and item_id not in playing_file and playing_file in playlist_data:
            # if the current now_playing data isn't correct, pull it from the playlist_data
            play_data = playlist_data.pop(playing_file)
            # Update now_playing data
            home_window.set_property('playlist', json.dumps(playlist_data))

        play_data["current_position"] = play_time
        play_data["duration"] = total_play_time
        played_information[item_id] = play_data
        home_window.set_property('now_playing', json.dumps(play_data))
        home_window.set_property('played_information', json.dumps(played_information))
        return play_data

    return {}


def get_play_url(media_source, play_session_id, channel_id=None):
    log.debug("get_play_url - media_source: {0}", media_source)

    # check if strm file Container
    if media_source.get('Container') == 'strm':
        log.debug("Detected STRM Container")
        playurl, listitem_props = get_strm_details(media_source)
        if playurl is None:
            log.debug("Error, no strm content")
            return None, None, None
        else:
            return playurl, "0", listitem_props

    # get all the options
    server = settings.getSetting('server_address')
    allow_direct_file_play = settings.getSetting('allow_direct_file_play') == 'true'

    can_direct_play = media_source["SupportsDirectPlay"]
    can_direct_stream = media_source["SupportsDirectStream"]
    can_transcode = media_source["SupportsTranscoding"]

    playurl = None
    playback_type = None

    # check if file can be directly played
    if allow_direct_file_play and can_direct_play:
        direct_path = media_source["Path"]
        direct_path = direct_path.replace("\\", "/")
        direct_path = direct_path.strip()

        # handle DVD structure
        container = media_source["Container"]
        if container == "dvd":
            direct_path = direct_path + "/VIDEO_TS/VIDEO_TS.IFO"
        elif container == "bluray":
            direct_path = direct_path + "/BDMV/index.bdmv"

        if direct_path.startswith("//"):
            direct_path = "smb://" + direct_path[2:]

        log.debug("playback_direct_path: {0}".format(direct_path))

        if xbmcvfs.exists(direct_path):
            playurl = direct_path
            playback_type = "0"

    # check if file can be direct streamed/played
    if (can_direct_stream or can_direct_play) and playurl is None:
        item_id = media_source.get('Id')
        if channel_id:
            # live tv has to be transcoded by the server
            playurl = None
        else:
            url_root = '{}/Videos/{}/stream'.format(server, item_id)
            play_params = {
                'static': True,
                'PlaySessionId': play_session_id,
                'MediaSourceId': item_id,
            }
            play_param_string = urlencode(play_params)
            playurl = '{}?{}'.format(url_root, play_param_string)
        playback_type = "1"

    # check is file can be transcoded
    if can_transcode and playurl is None:
        item_id = media_source.get('Id')
        device_id = get_device_id()

        user_details = load_user_details()
        user_token = user_details.get('token')
        bitrate = get_bitrate(settings.getSetting("force_max_stream_bitrate"))
        playback_max_width = settings.getSetting("playback_max_width")
        audio_codec = settings.getSetting("audio_codec")
        audio_playback_bitrate = settings.getSetting("audio_playback_bitrate")
        audio_bitrate = int(audio_playback_bitrate) * 1000
        audio_max_channels = settings.getSetting("audio_max_channels")
        playback_video_force_8 = settings.getSetting("playback_video_force_8") == "true"

        transcode_params = {
            "MediaSourceId": item_id,
            "DeviceId": device_id,
            "PlaySessionId": play_session_id,
            "api_key": user_token,
            "SegmentContainer": "ts",
            "VideoCodec": "h264",
            "VideoBitrate": bitrate,
            "MaxWidth": playback_max_width,
            "AudioCodec": audio_codec,
            "TranscodingMaxAudioChannels": audio_max_channels,
            "AudioBitrate": audio_bitrate
        }
        if playback_video_force_8:
            transcode_params.update({"MaxVideoBitDepth": "8"})

        # We need to include the channel ID if this is a live stream
        if channel_id:
            if media_source.get('LiveStreamId'):
                transcode_params['LiveStreamId'] = media_source.get('LiveStreamId')
            transcode_path = urlencode(transcode_params)
            playurl = '{}/Videos/{}/master.m3u8?{}'.format(
                server, channel_id, transcode_path)
        else:
            transcode_path = urlencode(transcode_params)
            playurl = '{}/Videos/{}/master.m3u8?{}'.format(
                server, item_id, transcode_path)

        playback_type = "2"

    return playurl, playback_type, []


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
        log.debug("STRM Line: {0}".format(line))
        if line.startswith('#KODIPROP:'):
            match = re.search('#KODIPROP:(?P<item_property>[^=]+?)=(?P<property_value>.+)', line)
            if match:
                item_property = match.group('item_property')
                property_value = match.group('property_value')
                log.debug("STRM property found: {0} value: {1}".format(item_property, property_value))
                listitem_props.append((item_property, property_value))
            else:
                log.debug("STRM #KODIPROP incorrect format")
        elif line.startswith('#'):
            #  unrecognized, treat as comment
            log.debug("STRM unrecognized line identifier, ignored")
        elif line != '':
            playurl = line
            log.debug("STRM playback url found")

    log.debug("Playback URL: {0} ListItem Properties: {1}".format(playurl, listitem_props))
    return playurl, listitem_props


class Service(xbmc.Player):

    def __init__(self, *args):
        log.debug("Starting monitor service: {0}".format(args))

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        stop_all_playback()

        if not xbmc.Player().isPlaying():
            log.debug("onPlayBackStarted: not playing file!")
            return

        play_data = get_playing_data()

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

        home_window = HomeWindow()
        played_information_string = home_window.get_property('played_information')
        played_information = json.loads(played_information_string)
        played_information[jellyfin_item_id] = play_data
        home_window.set_property('played_information', json.dumps(played_information))

        log.debug("Sending Playback Started")
        postdata = {
            'QueueableMediaTypes': "Video",
            'CanSeek': True,
            'ItemId': jellyfin_item_id,
            'MediaSourceId': jellyfin_source_id,
            'PlayMethod': playback_type,
            'PlaySessionId': play_session_id
        }

        log.debug("Sending POST play started: {0}".format(postdata))

        url = "/Sessions/Playing"
        api.post(url, postdata)

        home_screen = HomeWindow()
        home_screen.set_property("currently_playing_id", str(jellyfin_item_id))

    def onPlayBackEnded(self):
        # Will be called when kodi stops playing a file
        log.debug("onPlayBackEnded")
        stop_all_playback()

    def onPlayBackStopped(self):
        # Will be called when user stops kodi playing a file
        log.debug("onPlayBackStopped")
        stop_all_playback()

    def onPlayBackPaused(self):
        # Will be called when kodi pauses the video
        log.debug("onPlayBackPaused")

        play_data = get_playing_data()

        if play_data is not None:
            play_data['paused'] = True
            send_progress()

    def onPlayBackResumed(self):
        # Will be called when kodi resumes the video
        log.debug("onPlayBackResumed")

        play_data = get_playing_data()

        if play_data is not None:
            play_data['paused'] = False
            send_progress()

    def onPlayBackSeek(self, time, seek_offset):
        # Will be called when kodi seeks in video
        log.debug("onPlayBackSeek")
        send_progress()


class PlaybackService(xbmc.Monitor):
    background_image_cache_thread = None

    def __init__(self, monitor):
        self.monitor = monitor

    def onNotification(self, sender, method, data):
        if method == 'GUI.OnScreensaverActivated':
            self.screensaver_activated()
            return
        elif method == 'GUI.OnScreensaverDeactivated':
            self.screensaver_deactivated()
            return
        elif method == 'System.OnQuit':
            home_window = HomeWindow()
            home_window.set_property('exit', 'True')
            return

        if sender.lower() not in (
            'plugin.video.jellycon', 'xbmc', 'upnextprovider.signal'
        ):
            return


        signal = method.split('.', 1)[-1]
        if signal not in (
            "jellycon_play_action", "jellycon_play_youtube_trailer_action",
            "set_view", "plugin.video.jellycon_play_action"):
            return

        data_json = json.loads(data)
        if sender.lower() == "upnextprovider.signal":
            play_info = json.loads(binascii.unhexlify(data_json[0]))
        else:
            play_info = data_json[0]

        log.debug("PlaybackService:onNotification:{0}".format(play_info))

        if signal in (
            "jellycon_play_action", "plugin.video.jellycon_play_action"
        ):
            play_file(play_info)
        elif signal == "jellycon_play_youtube_trailer_action":
            trailer_link = play_info["url"]
            xbmc.executebuiltin(trailer_link)
        elif signal == "set_view":
            view_id = play_info["view_id"]
            log.debug("Setting view id: {0}".format(view_id))
            xbmc.executebuiltin("Container.SetViewMode(%s)" % int(view_id))

    def screensaver_activated(self):
        log.debug("Screen Saver Activated")

        home_screen = HomeWindow()
        home_screen.clear_property("skip_select_user")

        stop_playback = settings.getSetting("stopPlaybackOnScreensaver") == 'true'

        if stop_playback:
            player = xbmc.Player()
            if player.isPlayingVideo():
                log.debug("Screen Saver Activated : isPlayingVideo() = true")
                play_data = get_playing_data()
                if play_data:
                    log.debug("Screen Saver Activated : this is an JellyCon item so stop it")
                    player.stop()

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

        show_change_user = settings.getSetting('changeUserOnScreenSaver') == 'true'
        if show_change_user:
            home_screen = HomeWindow()
            skip_select_user = home_screen.get_property("skip_select_user")
            if skip_select_user is not None and skip_select_user == "true":
                return
            xbmc.executebuiltin("RunScript(plugin.video.jellycon,0,?mode=CHANGE_USER)")


def get_item_playback_info(item_id, force_transcode):

    filtered_codecs = []
    if settings.getSetting("force_transcode_h265") == "true":
        filtered_codecs.append("hevc")
        filtered_codecs.append("h265")
    if settings.getSetting("force_transcode_mpeg2") == "true":
        filtered_codecs.append("mpeg2video")
    if settings.getSetting("force_transcode_msmpeg4v3") == "true":
        filtered_codecs.append("msmpeg4v3")
    if settings.getSetting("force_transcode_mpeg4") == "true":
        filtered_codecs.append("mpeg4")
    if settings.getSetting("force_transcode_av1") == "true":
        filtered_codecs.append("av1")

    if not force_transcode:
        bitrate = get_bitrate(settings.getSetting("max_stream_bitrate"))
    else:
        bitrate = get_bitrate(settings.getSetting("force_max_stream_bitrate"))

    audio_codec = settings.getSetting("audio_codec")
    audio_playback_bitrate = settings.getSetting("audio_playback_bitrate")
    audio_max_channels = settings.getSetting("audio_max_channels")

    audio_bitrate = int(audio_playback_bitrate) * 1000

    profile = {
        "Name": "Kodi",
        "MaxStaticBitrate": bitrate,
        "MaxStreamingBitrate": bitrate,
        "MusicStreamingTranscodingBitrate": audio_bitrate,
        "TimelineOffsetSeconds": 5,
        "TranscodingProfiles": [
            {
                "Type": "Audio"
            },
            {
                "Container": "ts",
                "Protocol": "hls",
                "Type": "Video",
                "AudioCodec": audio_codec,
                "VideoCodec": "h264",
                "MaxAudioChannels": audio_max_channels
            },
            {
                "Container": "jpeg",
                "Type": "Photo"
            }
        ],
        "DirectPlayProfiles": [
            {
                "Type": "Video"
            },
            {
                "Type": "Audio"
            },
            {
                "Type": "Photo"
            }
        ],
        "ResponseProfiles": [],
        "ContainerProfiles": [],
        "CodecProfiles": [],
        "SubtitleProfiles": [
            {
                "Format": "srt",
                "Method": "External"
            },
            {
                "Format": "srt",
                "Method": "Embed"
            },
            {
                "Format": "ass",
                "Method": "External"
            },
            {
                "Format": "ass",
                "Method": "Embed"
            },
            {
                "Format": "sub",
                "Method": "Embed"
            },
            {
                "Format": "sub",
                "Method": "External"
            },
            {
                "Format": "ssa",
                "Method": "Embed"
            },
            {
                "Format": "ssa",
                "Method": "External"
            },
            {
                "Format": "smi",
                "Method": "Embed"
            },
            {
                "Format": "smi",
                "Method": "External"
            },
            {
                "Format": "pgssub",
                "Method": "Embed"
            },
            {
                "Format": "pgssub",
                "Method": "External"
            },
            {
                "Format": "dvdsub",
                "Method": "Embed"
            },
            {
                "Format": "dvdsub",
                "Method": "External"
            },
            {
                "Format": "pgs",
                "Method": "Embed"
            },
            {
                "Format": "pgs",
                "Method": "External"
            }
        ]
    }

    if len(filtered_codecs) > 0:
        profile['DirectPlayProfiles'][0]['VideoCodec'] = "-%s" % ",".join(filtered_codecs)

    if force_transcode:
        profile['DirectPlayProfiles'] = []

    if settings.getSetting("playback_video_force_8") == "true":
        profile['CodecProfiles'].append(
            {
                "Type": "Video",
                "Codec": "h264",
                "Conditions": [
                    {
                        "Condition": "LessThanEqual",
                        "Property": "VideoBitDepth",
                        "Value": "8",
                        "IsRequired": False
                    }
                ]
            }
        )
        profile['CodecProfiles'].append(
            {
                "Type": "Video",
                "Codec": "h265,hevc",
                "Conditions": [
                    {
                        "Condition": "EqualsAny",
                        "Property": "VideoProfile",
                        "Value": "main"
                    }
                ]
            }
        )

    playback_info = {
        'UserId': api.user_id,
        'DeviceProfile': profile,
        'AutoOpenLiveStream': True
    }

    if force_transcode:
        url = "/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s&EnableDirectPlay=false&EnableDirectStream=false" % (item_id, bitrate)
    else:
        url = "/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s" % (item_id, bitrate)

    log.debug("PlaybackInfo : {0}".format(url))
    log.debug("PlaybackInfo : {0}".format(profile))
    play_info_result = api.post(url, playback_info)
    log.debug("PlaybackInfo : {0}".format(play_info_result))

    return play_info_result
