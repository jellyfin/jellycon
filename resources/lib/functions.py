# Gnu General Public License - see LICENSE.TXT

import urllib
import sys
import os
import time
import cProfile
import pstats
import json
import StringIO
import encodings
import binascii
import re
import hashlib
import cPickle

import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc

from .downloadutils import DownloadUtils
from .utils import getArt, send_event_notification
from .kodi_utils import HomeWindow
from .clientinfo import ClientInformation
from .datamanager import DataManager
from .server_detect import checkServer
from .simple_logging import SimpleLogging
from .menu_functions import displaySections, showMovieAlphaList, showGenreList, showWidgets, show_search, showMoviePages
from .translation import string_load
from .server_sessions import showServerSessions
from .action_menu import ActionMenu
from .widgets import getWidgetContent, get_widget_content_cast#, getWidgetUrlContent
import trakttokodi
from .item_functions import add_gui_item, extract_item_info, ItemDetails
from .cache_images import CacheArtwork
from dir_functions import getContent, processDirectory

__addon__ = xbmcaddon.Addon()
__addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__cwd__ = __addon__.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath(os.path.join(__cwd__))

log = SimpleLogging(__name__)

kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

downloadUtils = DownloadUtils()
dataManager = DataManager()


def mainEntryPoint():
    log.debug("===== EmbyCon START =====")

    settings = xbmcaddon.Addon()
    profile_code = settings.getSetting('profile') == "true"
    pr = None
    if profile_code:
        return_value = xbmcgui.Dialog().yesno("Profiling Enabled", "Do you want to run profiling?")
        if return_value:
            pr = cProfile.Profile()
            pr.enable()

    log.debug("Running Python: {0}", sys.version_info)
    log.debug("Running EmbyCon: {0}", ClientInformation().getVersion())
    log.debug("Kodi BuildVersion: {0}", xbmc.getInfoLabel("System.BuildVersion"))
    log.debug("Kodi Version: {0}", kodi_version)
    log.debug("Script argument data: {0}", sys.argv)

    try:
        params = get_params(sys.argv[2])
    except:
        params = {}

    home_window = HomeWindow()

    if len(params) == 0:
        window_params = home_window.getProperty("Params")
        log.debug("windowParams: {0}", window_params)
        # home_window.clearProperty("Params")
        if window_params:
            try:
                params = get_params(window_params)
            except:
                params = {}

    log.debug("Script params: {0}", params)

    param_url = params.get('url', None)

    if param_url:
        param_url = urllib.unquote(param_url)

    mode = params.get("mode", None)

    if mode == "CHANGE_USER":
        checkServer(change_user=True, notify=False)
    elif mode == "CACHE_ARTWORK":
        CacheArtwork().cache_artwork_interactive()
    elif mode == "DETECT_SERVER":
        checkServer(force=True, notify=True)
    elif mode == "DETECT_SERVER_USER":
        checkServer(force=True, change_user=True, notify=False)
    elif mode == "playTrailer":
        item_id = params["id"]
        playTrailer(item_id)
    elif mode == "MOVIE_ALPHA":
        showMovieAlphaList()
    elif mode == "GENRES":
        showGenreList(params)
    elif mode == "MOVIE_PAGES":
        showMoviePages(params)
    elif mode == "WIDGETS":
        showWidgets()
    elif mode == "TOGGLE_WATCHED":
        toggle_watched(params)
    elif mode == "SHOW_MENU":
        show_menu(params)
    elif mode == "SHOW_SETTINGS":
        __addon__.openSettings()
        WINDOW = xbmcgui.getCurrentWindowId()
        if WINDOW == 10000:
            log.debug("Currently in home - refreshing to allow new settings to be taken")
            xbmc.executebuiltin("ActivateWindow(Home)")
    elif mode == "WIDGET_CONTENT":
        getWidgetContent(int(sys.argv[1]), params)
    elif mode == "WIDGET_CONTENT_CAST":
        get_widget_content_cast(int(sys.argv[1]), params)
    #elif mode == "WIDGET_CONTENT_URL":
    #    getWidgetUrlContent(int(sys.argv[1]), params)
    elif mode == "PARENT_CONTENT":
        checkServer(notify=False)
        showParentContent(params)
    elif mode == "SHOW_CONTENT":
        # plugin://plugin.video.embycon?mode=SHOW_CONTENT&item_type=Movie|Series
        checkServer(notify=False)
        showContent(sys.argv[0], int(sys.argv[1]), params)
    elif mode == "SEARCH":
        # plugin://plugin.video.embycon?mode=SEARCH
        checkServer(notify=False)
        xbmcplugin.setContent(int(sys.argv[1]), 'files')
        show_search()
    elif mode == "NEW_SEARCH":
        checkServer(notify=False)
        search_results(params)
    elif mode == "NEW_SEARCH_PERSON":
        checkServer(notify=False)
        search_results_person(params)
    elif mode == "SHOW_SERVER_SESSIONS":
        checkServer(notify=False)
        showServerSessions()
    elif mode == "TRAKTTOKODI":
        checkServer(notify=False)
        trakttokodi.entry_point(params)
    else:
        checkServer(notify=False)
        log.debug("EmbyCon -> Mode: {0}", mode)
        log.debug("EmbyCon -> URL: {0}", param_url)

        if mode == "GET_CONTENT":
            getContent(param_url, params)
        elif mode == "PLAY":
            PLAY(params)
        else:
            displaySections()

    if (pr):
        pr.disable()

        fileTimeStamp = time.strftime("%Y%m%d-%H%M%S")
        tabFileName = __addondir__ + "profile(" + fileTimeStamp + ").txt"
        s = StringIO.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps = ps.sort_stats('cumulative')
        ps.print_stats()
        ps.strip_dirs()
        ps = ps.sort_stats('tottime')
        ps.print_stats()
        with open(tabFileName, 'wb') as f:
            f.write(s.getvalue())

    log.debug("===== EmbyCon FINISHED =====")


def toggle_watched(params):
    log.debug("toggle_watched: {0}", params)
    item_id = params.get("item_id", None)
    if item_id is None:
        return
    url = "{server}/emby/Users/{userid}/Items/" + item_id + "?format=json"
    data_manager = DataManager()
    result = data_manager.GetContent(url)
    log.debug("toggle_watched item info: {0}", result)

    user_data = result.get("UserData", None)
    if user_data is None:
        return

    if user_data.get("Played", False) is False:
        markWatched(item_id)
    else:
        markUnwatched(item_id)


def markWatched(item_id):
    log.debug("Mark Item Watched: {0}", item_id)
    url = "{server}/emby/Users/{userid}/PlayedItems/" + item_id
    downloadUtils.downloadUrl(url, postBody="", method="POST")
    home_window = HomeWindow()
    home_window.setProperty("embycon_widget_reload", str(time.time()))

    last_url = home_window.getProperty("last_content_url")
    if last_url:
        log.debug("markWatched_lastUrl: {0}", last_url)
        home_window.setProperty("skip_cache_for_" + last_url, "true")

    xbmc.executebuiltin("Container.Refresh")


def markUnwatched(item_id):
    log.debug("Mark Item UnWatched: {0}", item_id)
    url = "{server}/emby/Users/{userid}/PlayedItems/" + item_id
    downloadUtils.downloadUrl(url, method="DELETE")
    home_window = HomeWindow()
    home_window.setProperty("embycon_widget_reload", str(time.time()))

    last_url = home_window.getProperty("last_content_url")
    if last_url:
        log.debug("markUnwatched_lastUrl: {0}", last_url)
        home_window.setProperty("skip_cache_for_" + last_url, "true")

    xbmc.executebuiltin("Container.Refresh")


def markFavorite(item_id):
    log.debug("Add item to favourites: {0}", item_id)
    url = "{server}/emby/Users/{userid}/FavoriteItems/" + item_id
    downloadUtils.downloadUrl(url, postBody="", method="POST")
    home_window = HomeWindow()
    home_window.setProperty("embycon_widget_reload", str(time.time()))

    last_url = home_window.getProperty("last_content_url")
    if last_url:
        home_window.setProperty("skip_cache_for_" + last_url, "true")

    xbmc.executebuiltin("Container.Refresh")


def unmarkFavorite(item_id):
    log.debug("Remove item from favourites: {0}", item_id)
    url = "{server}/emby/Users/{userid}/FavoriteItems/" + item_id
    downloadUtils.downloadUrl(url, method="DELETE")
    home_window = HomeWindow()
    home_window.setProperty("embycon_widget_reload", str(time.time()))

    last_url = home_window.getProperty("last_content_url")
    if last_url:
        home_window.setProperty("skip_cache_for_" + last_url, "true")

    xbmc.executebuiltin("Container.Refresh")


def delete(item):

    item_id = item.get("Id")
    item_name = item.get("Name")
    series_name = item.get("SeriesName")
    if series_name:
        final_name = series_name + " - " + item_name
    else:
        final_name = item_name

    return_value = xbmcgui.Dialog().yesno(string_load(30091), final_name, string_load(30092))
    if return_value:
        log.debug('Deleting Item: {0}', item_id)
        url = '{server}/emby/Items/' + item_id
        progress = xbmcgui.DialogProgress()
        progress.create(string_load(30052), string_load(30053))
        downloadUtils.downloadUrl(url, method="DELETE")
        progress.close()
        home_window = HomeWindow()
        home_window.setProperty("embycon_widget_reload", str(time.time()))

        last_url = home_window.getProperty("last_content_url")
        if last_url:
            home_window.setProperty("skip_cache_for_" + last_url, "true")

        xbmc.executebuiltin("Container.Refresh")


def get_params(paramstring):
    log.debug("Parameter string: {0}", paramstring)
    param = {}
    if len(paramstring) >= 2:
        params = paramstring

        if params[0] == "?":
            cleanedparams = params[1:]
        else:
            cleanedparams = params

        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]

        pairsofparams = cleanedparams.split('&')
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
            elif (len(splitparams)) == 3:
                param[splitparams[0]] = splitparams[1] + "=" + splitparams[2]

    log.debug("EmbyCon -> Detected parameters: {0}", param)
    return param


def show_menu(params):
    log.debug("showMenu(): {0}", params)

    item_id = params["item_id"]

    url = "{server}/emby/Users/{userid}/Items/" + item_id + "?format=json"
    data_manager = DataManager()
    result = data_manager.GetContent(url)
    log.debug("Playfile item info: {0}", result)

    if result is None:
        return

    action_items = []

    if result["Type"] in ["Episode", "Movie", "Music", "Video", "Audio", "TvChannel", "Program"]:
        li = xbmcgui.ListItem(string_load(30314))
        li.setProperty('menu_id', 'play')
        action_items.append(li)

    if result["Type"] in ["Season", "MusicAlbum"]:
        li = xbmcgui.ListItem(string_load(30317))
        li.setProperty('menu_id', 'play_all')
        action_items.append(li)

    if result["Type"] in ["Episode", "Movie", "Video", "TvChannel", "Program"]:
        li = xbmcgui.ListItem(string_load(30275))
        li.setProperty('menu_id', 'transcode')
        action_items.append(li)

    if result["Type"] == "Movie":
        li = xbmcgui.ListItem(string_load(30307))
        li.setProperty('menu_id', 'play_trailer')
        action_items.append(li)

    if result["Type"] == "Episode" and result["ParentId"] is not None:
        li = xbmcgui.ListItem(string_load(30327))
        li.setProperty('menu_id', 'view_season')
        action_items.append(li)

    if result["Type"] == "Series":
        li = xbmcgui.ListItem(string_load(30354))
        li.setProperty('menu_id', 'view_series')
        action_items.append(li)

    user_data = result.get("UserData", None)
    if user_data:
        progress = user_data.get("PlaybackPositionTicks", 0) != 0
        played = user_data.get("Played", False)
        if not played or progress:
            li = xbmcgui.ListItem(string_load(30270))
            li.setProperty('menu_id', 'mark_watched')
            action_items.append(li)
        if played or progress:
            li = xbmcgui.ListItem(string_load(30271))
            li.setProperty('menu_id', 'mark_unwatched')
            action_items.append(li)

        if user_data.get("IsFavorite", False) == False:
            li = xbmcgui.ListItem(string_load(30272))
            li.setProperty('menu_id', 'emby_set_favorite')
            action_items.append(li)
        else:
            li = xbmcgui.ListItem(string_load(30273))
            li.setProperty('menu_id', 'emby_unset_favorite')
            action_items.append(li)

    li = xbmcgui.ListItem(string_load(30274))
    li.setProperty('menu_id', 'delete')
    action_items.append(li)

    li = xbmcgui.ListItem(string_load(30281))
    li.setProperty('menu_id', 'refresh_images')
    action_items.append(li)

    #xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)

    action_menu = ActionMenu("ActionMenu.xml", PLUGINPATH, "default", "720p")
    action_menu.setActionItems(action_items)
    action_menu.doModal()
    selected_action_item = action_menu.getActionItem()
    selected_action = ""
    if selected_action_item is not None:
        selected_action = selected_action_item.getProperty('menu_id')
    log.debug("Menu Action Selected: {0}", selected_action_item)
    del action_menu

    if selected_action == "play":
        log.debug("Play Item")
        #list_item = populate_listitem(params["item_id"])
        #result = xbmcgui.Dialog().info(list_item)
        #log.debug("xbmcgui.Dialog().info: {0}", result)
        PLAY(params)

    elif selected_action == "play_all":
        PLAY(params)

    elif selected_action == "play_trailer":
        playTrailer(item_id)

    elif selected_action == "transcode":
        params['force_transcode'] = 'true'
        PLAY(params)

    elif selected_action == "emby_set_favorite":
        markFavorite(item_id)

    elif selected_action == "emby_unset_favorite":
        unmarkFavorite(item_id)

    elif selected_action == "mark_watched":
        markWatched(item_id)

    elif selected_action == "mark_unwatched":
        markUnwatched(item_id)

    elif selected_action == "delete":
        delete(result)

    elif selected_action == "view_season":
        xbmc.executebuiltin("Dialog.Close(all,true)")
        parent_id = result["ParentId"]
        series_id = result["SeriesId"]
        u = ('{server}/emby/Shows/' + series_id +
             '/Episodes'
             '?userId={userid}' +
             '&seasonId=' + parent_id +
             '&IsVirtualUnAired=false' +
             '&IsMissing=false' +
             '&Fields={field_filters}' +
             '&format=json')
        action_url = ("plugin://plugin.video.embycon/?url=" + urllib.quote(u) + "&mode=GET_CONTENT&media_type=Season")
        built_in_command = 'ActivateWindow(Videos, ' + action_url + ', return)'
        xbmc.executebuiltin(built_in_command)

    elif selected_action == "view_series":
        xbmc.executebuiltin("Dialog.Close(all,true)")
        u = ('{server}/emby/Shows/' + item_id +
             '/Seasons'
             '?userId={userid}' +
             '&Fields={field_filters}' +
             '&format=json')
        action_url = ("plugin://plugin.video.embycon/?url=" + urllib.quote(u) + "&mode=GET_CONTENT&media_type=Series")
        built_in_command = 'ActivateWindow(Videos, ' + action_url + ', return)'
        xbmc.executebuiltin(built_in_command)

    elif selected_action == "refresh_images":
        CacheArtwork().delete_cached_images(item_id)


def populate_listitem(item_id):
    log.debug("populate_listitem: {0}", item_id)

    url = "{server}/emby/Users/{userid}/Items/" + item_id + "?format=json"
    jsonData = downloadUtils.downloadUrl(url)
    result = json.loads(jsonData)
    log.debug("populate_listitem item info: {0}", result)

    '''
    server = downloadUtils.getServer()
    gui_options = {}
    gui_options["server"] = server

    gui_options["name_format"] = None
    gui_options["name_format_type"] = None

    details, extraData = extract_item_info(result,gui_options )
    u, list_item, folder = add_gui_item(result["Id"], details, extraData, {}, folder=False)

    log.debug("list_item path: {0}", u)

    #list_item.setProperty('IsPlayable', 'false')
    #list_item.setPath(u)
    '''

    item_title = result.get("Name", string_load(30280))

    list_item = xbmcgui.ListItem(label=item_title)

    server = downloadUtils.getServer()

    art = getArt(result, server=server)
    list_item.setIconImage(art['thumb'])  # back compat
    list_item.setProperty('fanart_image', art['fanart'])  # back compat
    list_item.setProperty('discart', art['discart'])  # not avail to setArt
    list_item.setArt(art)

    list_item.setProperty('IsPlayable', 'false')
    list_item.setProperty('IsFolder', 'false')
    list_item.setProperty('id', result.get("Id"))

    # play info
    details = {
        'title': item_title,
        'plot': result.get("Overview")
    }

    list_item.setInfo("Video", infoLabels=details)

    return list_item


def showContent(pluginName, handle, params):
    log.debug("showContent Called: {0}", params)

    item_type = params.get("item_type")
    settings = xbmcaddon.Addon()
    group_movies = settings.getSetting('group_movies') == "true"

    if item_type.lower().find("movie") == -1:
        group_movies = False

    contentUrl = ("{server}/emby/Users/{userid}/Items"
                  "?format=json" +
                  "&ImageTypeLimit=1" +
                  "&IsMissing=False" +
                  "&Fields={field_filters}" +
                  '&CollapseBoxSetItems=' + str(group_movies) +
                  '&GroupItemsIntoCollections=' + str(group_movies) +
                  "&Recursive=true" +
                  "&IsVirtualUnaired=false" +
                  "&IncludeItemTypes=" + item_type)

    log.debug("showContent Content Url: {0}", contentUrl)
    getContent(contentUrl, params)


def showParentContent(params):
    log.debug("showParentContent Called: {0}", params)

    parentId = params.get("ParentId")

    contentUrl = (
        "{server}/emby/Users/{userid}/items?ParentId=" + parentId +
        "&IsVirtualUnaired=false" +
        "&IsMissing=False" +
        "&ImageTypeLimit=1" +
        "&Fields={field_filters}" +
        "&format=json")

    log.debug("showParentContent Content Url: {0}", contentUrl)
    getContent(contentUrl, params)


def search_results_person(params):

    handle = int(sys.argv[1])

    person_id = params.get("person_id")
    details_url = ('{server}/emby/Users/{userid}/items' +
                   '?PersonIds=' + person_id +
                   # '&IncludeItemTypes=Movie' +
                   '&Recursive=true' +
                   '&Fields={field_filters}' +
                   '&format=json')

    '''
    details_result = dataManager.GetContent(details_url)
    log.debug("Search Results Details: {0}", details_result)

    if details_result:
        items = details_result.get("Items")
        found_types = set()
        for item in items:
            found_types.add(item.get("Type"))
        log.debug("search_results_person found_types: {0}", found_types)
    '''
    dir_items, detected_type = processDirectory(details_url, None, params)

    log.debug('search_results_person results: {0}', dir_items)
    log.debug('search_results_person detect_type: {0}', detected_type)

    if detected_type is not None:
        # if the media type is not set then try to use the detected type
        log.debug("Detected content type: {0}", detected_type)
        content_type = None

        if detected_type == "Movie":
            content_type = 'movies'
        elif detected_type == "Episode":
            content_type = 'episodes'
        elif detected_type == "Series":
            content_type = 'tvshows'
        elif detected_type == "Music" or detected_type == "Audio" or detected_type == "Musicalbum":
            content_type = 'songs'

        if content_type:
            xbmcplugin.setContent(handle, content_type)

    #xbmcplugin.setContent(handle, detected_type)

    if dir_items is not None:
        xbmcplugin.addDirectoryItems(handle, dir_items)

    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

def search_results(params):

    item_type = params.get('item_type')
    query_string = params.get('query')
    if query_string:
        log.debug("query_string : {0}", query_string)
        query_string = urllib.unquote(query_string)
        log.debug("query_string : {0}", query_string)

    item_type = item_type.lower()

    if item_type == 'movie':
        heading_type = string_load(30231)
        content_type = 'movies'
    elif item_type == 'series':
        heading_type = string_load(30229)
        content_type = 'tvshows'
    elif item_type == 'episode':
        heading_type = string_load(30235)
        content_type = 'episodes'
        params["name_format"] = "Episode|episode_name_format"
    elif item_type == "music" or item_type == "audio" or item_type == "musicalbum":
        heading_type = 'Music'
        content_type = 'songs'
    elif item_type == "person":
        heading_type = 'Artists'
        content_type = 'artists'
    else:
        heading_type = item_type
        content_type = 'video'

    handle = int(sys.argv[1])

    if not query_string:
        home_window = HomeWindow()
        last_search = home_window.getProperty("last_search")
        kb = xbmc.Keyboard()
        kb.setHeading(heading_type.capitalize() + ' ' + string_load(30246).lower())
        kb.setDefault(last_search)
        kb.doModal()

        if kb.isConfirmed():
            user_input = kb.getText().strip()
        else:
            return

        home_window.setProperty("last_search", user_input)
        log.debug('searchResults Called: {0}', params)
        query = user_input

    else:
        query = query_string

    query = urllib.quote(query)
    log.debug("query : {0}", query)

    if (not item_type) or (not query):
        return

    limit = int(params.get('limit', 20))
    content_url = ('{server}/emby/Search/Hints?searchTerm=' + query +
                   '&UserId={userid}' +
                   '&Limit=' + str(limit) +
                   '&IncludeItemTypes=' + item_type +
                   '&ExcludeItemTypes=LiveTvProgram' +
                   '&IncludePeople=false' +
                   '&IncludeMedia=true' +
                   '&IncludeGenres=false' +
                   '&IncludeStudios=false' +
                   '&IncludeArtists=false')

    if item_type == "person":
        content_url = ('{server}/emby/Search/Hints?searchTerm=' + query +
                       '&UserId={userid}' +
                       '&Limit=' + str(limit) +
                       '&IncludePeople=true' +
                       '&IncludeMedia=false' +
                       '&IncludeGenres=false' +
                       '&IncludeStudios=false' +
                       '&IncludeArtists=false')



    # show a progress indicator if needed
    settings = xbmcaddon.Addon()
    progress = None
    if settings.getSetting('showLoadProgress') == "true":
        progress = xbmcgui.DialogProgress()
        progress.create(string_load(30112))
        progress.update(0, string_load(30113))

    search_hints_result = dataManager.GetContent(content_url)
    log.debug('SearchHints jsonData: {0}', search_hints_result)

    if search_hints_result is None:
        search_hints_result = {}

    search_hints = search_hints_result.get('SearchHints')
    if search_hints is None:
        search_hints = []

    total_results = int(search_hints_result.get('TotalRecordCount', 0))
    log.debug('SEARCH_TOTAL_RESULTS: {0}', total_results)

    # what type of search was it
    if item_type == "person":
        log.debug("Item Search Result")
        server = downloadUtils.getServer()
        list_items = []
        for item in search_hints:
            person_id = item.get('ItemId')
            person_name = item.get('Name')
            image_tag = item.get('PrimaryImageTag')
            person_thumbnail = downloadUtils.imageUrl(person_id, "Primary", 0, 400, 400, image_tag, server=server)

            action_url = sys.argv[0] + "?mode=NEW_SEARCH_PERSON&person_id=" + person_id

            list_item = xbmcgui.ListItem(label=person_name)
            list_item.setProperty("id", person_id)
            if person_thumbnail:
                art_links = {}
                art_links["thumb"] = person_thumbnail
                art_links["poster"] = person_thumbnail
                list_item.setArt(art_links)

            item_tupple = (action_url, list_item, True)
            list_items.append(item_tupple)

        xbmcplugin.setContent(handle, 'artists')
        xbmcplugin.addDirectoryItems(handle, list_items)
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

    else:
        # extract IDs for details query
        log.debug("Item Search Result")
        id_list = []
        for item in search_hints:
            item_id = item.get('ItemId')
            id_list.append(str(item_id))

        if len(id_list) > 0:
            Ids = ",".join(id_list)
            details_url = ('{server}/emby/Users/{userid}/items' +
                           '?Ids=' + Ids +
                           '&Fields={field_filters}' +
                           '&format=json')
            '''
            details_result = dataManager.GetContent(details_url)
            log.debug("Search Results Details: {0}", details_result)
            '''

            # set content type
            xbmcplugin.setContent(handle, content_type)

            dir_items, detected_type = processDirectory(details_url, progress, params)
            if dir_items is not None:
                xbmcplugin.addDirectoryItems(handle, dir_items)
                xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

        elif not query_string:
            xbmcgui.Dialog().ok(string_load(30335), string_load(30336))

    if progress is not None:
        progress.update(100, string_load(30125))
        progress.close()


def PLAY(params):
    log.debug("== ENTER: PLAY ==")

    log.debug("PLAY ACTION PARAMS: {0}", params)
    item_id = params.get("item_id")

    auto_resume = int(params.get("auto_resume", "-1"))
    log.debug("AUTO_RESUME: {0}", auto_resume)

    forceTranscode = params.get("force_transcode", None) is not None
    log.debug("FORCE_TRANSCODE: {0}", forceTranscode)

    media_source_id = params.get("media_source_id", "")
    log.debug("media_source_id: {0}", media_source_id)

    subtitle_stream_index = params.get("subtitle_stream_index")
    log.debug("subtitle_stream_index: {0}", subtitle_stream_index)

    audio_stream_index = params.get("audio_stream_index")
    log.debug("audio_stream_index: {0}", audio_stream_index)

    # set the current playing item id
    # set all the playback info, this will be picked up by the service
    # the service will then start the playback

    xbmc.Player().stop()

    play_info = {}
    play_info["item_id"] = item_id
    play_info["auto_resume"] = str(auto_resume)
    play_info["force_transcode"] = forceTranscode
    play_info["media_source_id"] = media_source_id
    play_info["subtitle_stream_index"] = subtitle_stream_index
    play_info["audio_stream_index"] = audio_stream_index
    log.info("Sending embycon_play_action : {0}", play_info)
    send_event_notification("embycon_play_action", play_info)


def playTrailer(id):
    log.debug("== ENTER: playTrailer ==")

    url = ("{server}/emby/Users/{userid}/Items/%s/LocalTrailers?format=json" % id)

    jsonData = downloadUtils.downloadUrl(url)
    result = json.loads(jsonData)

    if result is None:
        return

    log.debug("LocalTrailers {0}", result)
    count = 1

    trailer_names = []
    trailer_list = []
    for trailer in result:
        info = {}
        info["type"] = "local"
        name = trailer.get("Name")
        while not name or name in trailer_names:
            name = "Trailer " + str(count)
            count += 1
        info["name"] = name
        info["id"] = trailer.get("Id")
        count += 1
        trailer_names.append(name)
        trailer_list.append(info)

    url = ("{server}/emby/Users/{userid}/Items/%s?format=json&Fields=RemoteTrailers" % id)
    jsonData = downloadUtils.downloadUrl(url)
    result = json.loads(jsonData)
    log.debug("RemoteTrailers: {0}", result)
    count = 1

    if result is None:
        return

    remote_trailers = result.get("RemoteTrailers", [])
    for trailer in remote_trailers:
        info = {}
        info["type"] = "remote"
        url = trailer.get("Url", "none")
        if url.lower().find("youtube"):
            info["url"] = url
            name = trailer.get("Name")
            while not name or name in trailer_names:
                name = "Trailer " + str(count)
                count += 1
            info["name"] = name
            trailer_names.append(name)
            trailer_list.append(info)

    log.debug("TrailerList: {0}", trailer_list)

    trailer_text = []
    for trailer in trailer_list:
        name = trailer.get("name") + " (" + trailer.get("type") + ")"
        trailer_text.append(name)

    dialog = xbmcgui.Dialog()
    resp = dialog.select(string_load(30308), trailer_text)
    if resp > -1:
        trailer = trailer_list[resp]
        log.debug("SelectedTrailer: {0}", trailer)

        if trailer.get("type") == "local":
            params = {}
            params["item_id"] = trailer.get("id")
            PLAY(params)

        elif trailer.get("type") == "remote":
            youtube_id = trailer.get("url").rsplit('=', 1)[1]
            log.debug("YoutubeID: {0}", youtube_id)
            youtube_plugin = "PlayMedia(plugin://plugin.video.youtube/?action=play_video&videoid=%s)" % youtube_id
            xbmc.executebuiltin(youtube_plugin)



