# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import sys
import json
import urllib

import xbmcplugin
import xbmcaddon

from .downloadutils import DownloadUtils
from .kodi_utils import addMenuDirectoryItem, HomeWindow
from .simple_logging import SimpleLogging
from .translation import string_load
from .datamanager import DataManager
from .utils import getArt, get_emby_url

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()

__addon__ = xbmcaddon.Addon()

def show_movie_tags(params):
    log.debug("show_movie_tags: {0}", params)
    parent_id = params.get("parent_id")

    url_params = {}
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "SortName"
    url_params["SortOrder"] = "Ascending"
    url_params["CollapseBoxSetItems"] = False
    url_params["GroupItemsIntoCollections"] = False
    url_params["Recursive"] = True
    url_params["IsMissing"] = False
    url_params["EnableTotalRecordCount"] = False
    url_params["EnableUserData"] = False
    url_params["IncludeItemTypes"] = "Movie"

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Tags", url_params)
    data_manager = DataManager()
    result = data_manager.GetContent(url)

    if not result:
        return

    tags = result.get("Items")

    log.debug("Tags : {0}", result)

    for tag in tags:
        name = tag["Name"]
        tag_id = tag["Id"]

        url_params = {}
        url_params["IncludeItemTypes"] = "Movie"
        url_params["CollapseBoxSetItems"] = False
        url_params["GroupItemsIntoCollections"] = False
        url_params["Recursive"] = True
        url_params["IsMissing"] = False
        url_params["ImageTypeLimit"] = 1
        url_params["SortBy"] = "Name"
        url_params["SortOrder"] = "Ascending"
        url_params["Fields"] = "{field_filters}"
        url_params["TagIds"] = tag_id

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", url_params)

        content_url = urllib.quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}", name, url)
        addMenuDirectoryItem(name, url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_years(params):
    log.debug("show_movie_years: {0}", params)
    parent_id = params.get("parent_id")
    group_into_decades = params.get("group") == "true"

    url_params = {}
    url_params["UserId"] = "{userid}"
    url_params["SortBy"] = "SortName"
    url_params["SortOrder"] = "Ascending"
    url_params["CollapseBoxSetItems"] = False
    url_params["GroupItemsIntoCollections"] = False
    url_params["Recursive"] = True
    url_params["IsMissing"] = False
    url_params["EnableTotalRecordCount"] = False
    url_params["EnableUserData"] = False
    url_params["IncludeItemTypes"] = "Movie"

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Years", url_params)

    data_manager = DataManager()
    result = data_manager.GetContent(url)

    if not result:
        return

    years_list = result.get("Items")
    result_names = {}
    for year in years_list:
        name = year.get("Name")
        if group_into_decades:
            year_int = int(name)
            decade = str(year_int - year_int % 10)
            decade_end = str((year_int - year_int % 10) + 9)
            decade_name = decade + "-" + decade_end
            result_names[decade_name] = year_int - year_int % 10
        else:
            result_names[name] = [name]

    keys = list(result_names.keys())
    keys.sort()

    if group_into_decades:
        for decade_key in keys:
            year_list = []
            decade_start = result_names[decade_key]
            for include_year in range(decade_start, decade_start + 10):
                year_list.append(str(include_year))
            result_names[decade_key] = year_list

    for year in keys:
        name = year
        value = ",".join(result_names[year])

        params = {}
        params["IncludeItemTypes"] = "Movie"
        params["CollapseBoxSetItems"] = False
        params["GroupItemsIntoCollections"] = False
        params["Recursive"] = True
        params["IsMissing"] = False
        params["ImageTypeLimit"] = 1
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Fields"] = "{field_filters}"
        params["Years"] = value

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        content_url = urllib.quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}", name, url)
        addMenuDirectoryItem(name, url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_pages(params):
    log.debug("showMoviePages: {0}", params)

    parent_id = params.get("parent_id")
    settings = xbmcaddon.Addon()
    group_movies = settings.getSetting('group_movies') == "true"

    params = {}
    params["IncludeItemTypes"] = "Movie"
    params["CollapseBoxSetItems"] = str(group_movies)
    params["GroupItemsIntoCollections"] = str(group_movies)
    params["Recursive"] = True
    params["IsMissing"] = False
    params["ImageTypeLimit"] = 0

    if parent_id:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

    data_manager = DataManager()
    result = data_manager.GetContent(url)

    if result is None:
        return

    total_results = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}", total_results)

    if result == 0:
        return

    page_limit = int(settings.getSetting('moviePageSize'))
    if page_limit == 0:
        page_limit = 20

    start_index = 0
    collections = []

    while start_index < total_results:

        params = {}
        params["IncludeItemTypes"] = "Movie"
        params["CollapseBoxSetItems"] = str(group_movies)
        params["GroupItemsIntoCollections"] = str(group_movies)
        params["Recursive"] = True
        params["IsMissing"] = False
        params["ImageTypeLimit"] = 1
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Fields"] = "{field_filters}"
        params["StartIndex"] = start_index
        params["Limit"] = page_limit

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        item_data = {}
        item_data['title'] = "Page (" + str(start_index + 1) + " - " + str(page_upper) + ")"
        item_data['path'] = item_url
        item_data['media_type'] = 'movies'

        collections.append(item_data)
        start_index = start_index + page_limit

    for collection in collections:
        content_url = urllib.quote(collection['path'])
        url = sys.argv[0] + ("?url=" + content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), url, collection.get("art"))
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_genre_list(params):
    log.debug("showGenreList: {0}", params)

    server = downloadUtils.getServer()
    if server is None:
        return

    parent_id = params.get("parent_id")
    item_type = params.get("item_type")

    kodi_type = "Movies"
    emby_type = "Movie"
    if item_type is not None and item_type == "tvshow":
        emby_type = "Series"
        kodi_type = "tvshows"

    params = {}
    params["IncludeItemTypes"] = emby_type
    params["UserId"] = "{userid}"
    params["Recursive"] = True
    params["SortBy"] = "Name"
    params["SortOrder"] = "Ascending"
    params["ImageTypeLimit"] = 0

    if parent_id is not None:
        params["ParentId"] = parent_id

    url = get_emby_url("{server}/emby/Genres", params)

    data_manager = DataManager()
    result = data_manager.GetContent(url)

    if result is not None:
        result = result.get("Items")
    else:
        result = []

    settings = xbmcaddon.Addon()
    group_movies = settings.getSetting('group_movies') == "true"

    collections = []
    xbmcplugin.setContent(int(sys.argv[1]), 'genres')

    for genre in result:
        art = getArt(item=genre, server=server)
        item_data = {}
        item_data['title'] = genre.get("Name")
        item_data['media_type'] = kodi_type
        item_data['art'] = art

        params = {}
        params["Recursive"] = True
        params["CollapseBoxSetItems"] = str(group_movies)
        params["GroupItemsIntoCollections"] = str(group_movies)
        params["GenreIds"] = genre.get("Id")
        params["IncludeItemTypes"] = emby_type
        params["ImageTypeLimit"] = 1
        params["Fields"] = "{field_filters}"

        if parent_id is not None:
            params["ParentId"] = parent_id

        url = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        item_data['path'] = url
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + ("?url=" + urllib.quote(collection['path']) +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), url, collection.get("art"))
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_alpha_list(params):
    log.debug("== ENTER: showMovieAlphaList() ==")

    settings = xbmcaddon.Addon()
    server = downloadUtils.getServer()
    if server is None:
        return

    parent_id = params.get("parent_id")
    settings = xbmcaddon.Addon()
    group_movies = settings.getSetting('group_movies') == "true"

    collections = []

    item_data = {}
    item_data['title'] = "#"
    item_data['media_type'] = "Movies"

    params = {}
    params["Fields"] = "{field_filters}"
    params["CollapseBoxSetItems"] = str(group_movies)
    params["GroupItemsIntoCollections"] = str(group_movies)
    params["Recursive"] = True
    params["NameLessThan"] = "A"
    params["IncludeItemTypes"] = "Movie"
    params["SortBy"] = "Name"
    params["SortOrder"] = "Ascending"
    params["ImageTypeLimit"] = 1
    if parent_id is not None:
        params["ParentId"] = parent_id
    url = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    item_data['path'] = url

    collections.append(item_data)

    group_movies = settings.getSetting('group_movies') == "true"
    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                 "U", "V", "W", "X", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['title'] = alphaName
        item_data['media_type'] = "Movies"

        params = {}
        params["Fields"] = "{field_filters}"
        params["CollapseBoxSetItems"] = str(group_movies)
        params["GroupItemsIntoCollections"] = str(group_movies)
        params["Recursive"] = True
        params["NameStartsWith"] = alphaName
        params["IncludeItemTypes"] = "Movie"
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["ImageTypeLimit"] = 1
        if parent_id is not None:
            params["ParentId"] = parent_id
        url = get_emby_url("{server}/emby/Users/{userid}/Items", params)
        item_data['path'] = url

        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
               "&mode=GET_CONTENT&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_alpha_list(params):
    log.debug("== ENTER: showTvShowAlphaList() ==")

    settings = xbmcaddon.Addon()
    server = downloadUtils.getServer()
    if server is None:
        return

    parent_id = params.get("parent_id")

    collections = []

    item_data = {}
    item_data['title'] = "#"
    item_data['media_type'] = "tvshows"

    params = {}
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["NameLessThan"] = "A"
    params["IncludeItemTypes"] = "Series"
    params["SortBy"] = "Name"
    params["SortOrder"] = "Ascending"
    params["Recursive"] = True
    params["IsMissing"] = False
    if parent_id is not None:
        params["ParentId"] = parent_id
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)

    item_data['path'] = path
    collections.append(item_data)

    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                 "U", "V", "W", "X", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['title'] = alphaName
        item_data['media_type'] = "tvshows"

        params = {}
        params["Fields"] = "{field_filters}"
        params["ImageTypeLimit"] = 1
        params["NameStartsWith"] = alphaName
        params["IncludeItemTypes"] = "Series"
        params["SortBy"] = "Name"
        params["SortOrder"] = "Ascending"
        params["Recursive"] = True
        params["IsMissing"] = False
        if parent_id is not None:
            params["ParentId"] = parent_id
        path = get_emby_url("{server}/emby/Users/{userid}/Items", params)

        item_data['path'] = path
        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
               "&mode=GET_CONTENT&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def display_main_menu():
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    addMenuDirectoryItem(string_load(30406),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library")
    addMenuDirectoryItem(string_load(30407),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_global_types")
    addMenuDirectoryItem(string_load(30408),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_custom_widgets")
    addMenuDirectoryItem(string_load(30409),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=addon_items")

    xbmcplugin.endOfDirectory(handle)


def display_menu(params):
    menu_type = params.get("type")
    if menu_type == "library":
        display_library_views(params)
    elif menu_type == "library_item":
        display_library_view(params)
    elif menu_type == "show_global_types":
        show_global_types(params)
    elif menu_type == "global_list_movies":
        display_movies_type(params, None)
    elif menu_type == "global_list_tvshows":
        display_tvshow_type(params, None)
    elif menu_type == "show_custom_widgets":
        show_widgets()
    elif menu_type == "addon_items":
        display_addon_menu(params)
    elif menu_type == "show_movie_years":
        show_movie_years(params)
    elif menu_type == "show_movie_tags":
        show_movie_tags(params)


def show_global_types(params):
    handle = int(sys.argv[1])

    addMenuDirectoryItem(string_load(30256),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_movies")
    addMenuDirectoryItem(string_load(30261),
                         "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=global_list_tvshows")

    xbmcplugin.endOfDirectory(handle)


def display_homevideos_type(params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")
    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = False
    params["IsMissing"] = False
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1

    # All Home Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    params["Filters"] = "IsResumable"
    params["Recursive"] = True
    params["Limit"] = "{ItemLimit}"

    # In progress home movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    addMenuDirectoryItem(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsUnplayed,IsNotFolder"
    params["IsPlayed"] = False

    # Recently added
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    addMenuDirectoryItem(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    xbmcplugin.endOfDirectory(handle)


def display_addon_menu(params):

    addMenuDirectoryItem(string_load(30246), "plugin://plugin.video.embycon/?mode=SEARCH")
    addMenuDirectoryItem(string_load(30017), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
    addMenuDirectoryItem(string_load(30012), "plugin://plugin.video.embycon/?mode=CHANGE_USER")
    addMenuDirectoryItem(string_load(30011), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    addMenuDirectoryItem(string_load(30254), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")
    addMenuDirectoryItem(string_load(30395), "plugin://plugin.video.embycon/?mode=CLEAR_CACHE")
    addMenuDirectoryItem(string_load(30293), "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK")

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def display_collection_type(params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")

    params = {}
    params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Boxset"
    params["CollapseBoxSetItems"] = True
    params["GroupItemsIntoCollections"] = True
    params["Recursive"] = True
    params["IsMissing"] = False

    # All Collections
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_tvshow_type(params, view):
    handle = int(sys.argv[1])

    view_name = string_load(30261)
    if view is not None:
        view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    params = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["IsMissing"] = False
    params["IncludeItemTypes"] = "Series"
    params["Recursive"] = True

    # All TV Shows
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    params["Filters"] = "IsUnplayed"
    params["IsPlayed"] = False

    # Tv Shows with unplayed
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    addMenuDirectoryItem(view_name + string_load(30285), url)

    params["Limit"] = "{ItemLimit}"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsResumable"
    params["IncludeItemTypes"] = "Episode"

    # In progress episodes
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=Episodes"
    url += "&name_format=" + urllib.quote('Episode|episode_name_format')
    addMenuDirectoryItem(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsUnplayed"

    # Latest Episodes
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    addMenuDirectoryItem(view_name + string_load(30288) + " (" + show_x_filtered_items + ")", url)

    params["SortBy"] = "DateCreated"
    params["Filters"] = "IsUnplayed,IsNotFolder"

    # Recently Added
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=Episodes"
    url += "&name_format=" + urllib.quote('Episode|episode_name_format')
    addMenuDirectoryItem(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    params["Userid"] = "{userid}"

    # Next Up Episodes
    path = get_emby_url("{server}/emby/Shows/NextUp", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=Episodes"
    url += "&name_format=" + urllib.quote('Episode|episode_name_format')
    addMenuDirectoryItem(view_name + string_load(30278) + " (" + show_x_filtered_items + ")", url)

    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30325), path)

    path = "plugin://plugin.video.embycon/?mode=TVSHOW_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30404), path)

    xbmcplugin.endOfDirectory(handle)


def display_playlist_type(params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")

    params = {}
    params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1

    # All Playlists
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=playlists"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_music_type(params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "MusicAlbum"

    # all albums
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    addMenuDirectoryItem(view_name + string_load(30320), url)

    params = {}
    params["ParentId"] = view.get("Id")
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"

    # recently added
    path = get_emby_url("{server}/emby/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    addMenuDirectoryItem(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["Filters"] = "IsPlayed"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"

    # recently played
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    addMenuDirectoryItem(view_name + string_load(30349) + " (" + show_x_filtered_items + ")", url)

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Audio"
    params["Limit"] = "{ItemLimit}"
    params["Filters"] = "IsPlayed"
    params["SortBy"] = "PlayCount"
    params["SortOrder"] = "Descending"

    # most played
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    addMenuDirectoryItem(view_name + string_load(30353) + " (" + show_x_filtered_items + ")", url)

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = True
    params["ImageTypeLimit"] = 1

    # artists
    path = get_emby_url("{server}/emby/Artists/AlbumArtists", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=MusicArtists"
    addMenuDirectoryItem(view_name + string_load(30321), url)

    xbmcplugin.endOfDirectory(handle)


def display_musicvideos_type(params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    params = {}
    params["ParentId"] = view.get("Id")
    params["Recursive"] = False
    params["ImageTypeLimit"] = 1
    params["IsMissing"] = False
    params["Fields"] = "{field_filters}"

    # artists
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=musicvideos"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_livetv_type(params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    params = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"

    # channels
    path = get_emby_url("{server}/emby/LiveTv/Channels", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    addMenuDirectoryItem(view_name + string_load(30360), url)

    params = {}
    params["UserId"] = "{userid}"
    params["IsAiring"] = True
    params["ImageTypeLimit"] = 1
    params["Fields"] = "ChannelInfo,{field_filters}"
    params["EnableTotalRecordCount"] = False

    # programs
    path = get_emby_url("{server}/emby/LiveTv/Programs/Recommended", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    addMenuDirectoryItem(view_name + string_load(30361), url)

    params = {}
    params["UserId"] = "{userid}"
    params["Recursive"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"
    params["EnableTotalRecordCount"] = False

    # recordings
    path = get_emby_url("{server}/emby/LiveTv/Recordings", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    addMenuDirectoryItem(view_name + string_load(30362), url)

    xbmcplugin.endOfDirectory(handle)


def display_channel_type(params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    params = {}
    params["ParentId"] = view.get("Id")
    params["IsMissing"] = False
    params["ImageTypeLimit"] = 1
    params["Fields"] = "{field_filters}"

    # channels
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=files"
    addMenuDirectoryItem(view_name, url)

    xbmcplugin.endOfDirectory(handle)


def display_movies_type(params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = string_load(30256)
    if view is not None:
        view_name = view.get("Name")

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")
    group_movies = settings.getSetting('group_movies') == "true"

    params = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["IncludeItemTypes"] = "Movie"
    params["CollapseBoxSetItems"] = str(group_movies)
    params["GroupItemsIntoCollections"] = str(group_movies)
    params["Recursive"] = True
    params["IsMissing"] = False
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1

    # All Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    addMenuDirectoryItem(view_name + string_load(30405), url)

    params["Filters"] = "IsUnplayed"
    params["IsPlayed"] = False
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False

    # Unwatched Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    addMenuDirectoryItem(view_name + string_load(30285), url)

    params["IsPlayed"] = None
    params["Filters"] = "IsResumable"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Limit"] = "{ItemLimit}"

    # Resumable Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    addMenuDirectoryItem(view_name + string_load(30267) + " (" + show_x_filtered_items + ")", url)

    params["IsPlayed"] = False
    params["Filters"] = "IsUnplayed"
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsUnplayed,IsNotFolder"

    # Recently Added Movies
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=movies"
    addMenuDirectoryItem(view_name + string_load(30268) + " (" + show_x_filtered_items + ")", url)

    params = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["Fields"] = "{field_filters}"
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Boxset"
    params["CollapseBoxSetItems"] = True
    params["GroupItemsIntoCollections"] = True
    params["Recursive"] = True
    params["IsMissing"] = False

    # Collections
    path = get_emby_url("{server}/emby/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + urllib.quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    addMenuDirectoryItem(view_name + string_load(30410), url)

    path = "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30325), path)

    path = "plugin://plugin.video.embycon/?mode=MOVIE_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30397), path)

    path = "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30404), path)

    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30411), path)

    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_years&group=true"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30412), path)

    path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=show_movie_tags"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    addMenuDirectoryItem(view_name + string_load(30413), path)

    xbmcplugin.endOfDirectory(handle)


def display_library_views(params):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    server = downloadUtils.getServer()
    if server is None:
        return

    data_manager = DataManager()
    views_url = "{server}/emby/Users/{userid}/Views?format=json"
    views = data_manager.GetContent(views_url)
    if not views:
        return []
    views = views.get("Items")

    view_types = ["movies", "tvshows", "homevideos", "boxsets", "playlists", "music", "musicvideos", "livetv", "Channel"]

    for view in views:
        collection_type = view.get('CollectionType', None)
        item_type = view.get('Type', None)
        if collection_type in view_types or item_type == "Channel":
            view_name = view.get("Name")
            art = getArt(item=view, server=server)
            art['landscape'] = downloadUtils.getArtwork(view, "Primary", server=server)
            plugin_path = "plugin://plugin.video.embycon/?mode=SHOW_ADDON_MENU&type=library_item&view_id=" + view.get("Id")
            addMenuDirectoryItem(view_name, plugin_path, art=art)

    xbmcplugin.endOfDirectory(handle)


def display_library_view(params):
    node_id = params.get("view_id")

    view_info_url = "{server}/emby/Users/{userid}/Items/" + node_id
    data_manager = DataManager()
    view_info = data_manager.GetContent(view_info_url)

    log.debug("VIEW_INFO : {0}", view_info)

    collection_type = view_info.get("CollectionType", None)
    if collection_type is None and view_info.get('Type', None) == "Channel":
        collection_type = "channel"

    if collection_type == "movies":
        display_movies_type(params, view_info)
    elif collection_type == "playlists":
        display_playlist_type(params, view_info)
    elif collection_type == "tvshows":
        display_tvshow_type(params, view_info)
    elif collection_type == "boxsets":
        display_collection_type(params, view_info)
    elif collection_type == "homevideos":
        display_homevideos_type(params, view_info)
    elif collection_type == "music":
        display_music_type(params, view_info)
    elif collection_type == "musicvideos":
        display_musicvideos_type(params, view_info)
    elif collection_type == "livetv":
        display_livetv_type(params, view_info)
    elif collection_type == "channel":
        display_channel_type(params, view_info)


def displaySections():
    log.debug("== ENTER: displaySections() ==")
    xbmcplugin.setContent(int(sys.argv[1]), 'files')

    server = downloadUtils.getServer()
    if server is None:
        return

    # Add collections
    collections = getCollections()

    if collections:
        for collection in collections:
            if collection.get("item_type") == "plugin_link":
                plugin_path = collection['path']
                addMenuDirectoryItem(collection.get('title', string_load(30250)),
                                     plugin_path,
                                     art=collection.get("art"))
            else:
                url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
                       "&mode=GET_CONTENT&media_type=" + collection["media_type"])
                if collection.get("name_format") is not None:
                    url += "&name_format=" + urllib.quote(collection.get("name_format"))
                if not collection.get("use_cache", True):
                    url += "&use_cache=false"
                log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
                addMenuDirectoryItem(collection.get('title', string_load(30250)),
                                     url,
                                     art=collection.get("art"))

        addMenuDirectoryItem(string_load(30312) + string_load(30251),
                             "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie")
        addMenuDirectoryItem(string_load(30312) + string_load(30252), "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA")
        addMenuDirectoryItem(string_load(30312) + string_load(30266), "plugin://plugin.video.embycon/?mode=MOVIE_PAGES")

        addMenuDirectoryItem(string_load(30312) + string_load(30289),
                             "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow")
        addMenuDirectoryItem(string_load(30312) + string_load(30255),
                             "plugin://plugin.video.embycon/?mode=TVSHOW_ALPHA")

        addMenuDirectoryItem(string_load(30383) + string_load(30246), "plugin://plugin.video.embycon/?mode=SEARCH")
        addMenuDirectoryItem(string_load(30383) + string_load(30017),
                             "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
        addMenuDirectoryItem(string_load(30383) + string_load(30012), "plugin://plugin.video.embycon/?mode=CHANGE_USER")

    addMenuDirectoryItem(string_load(30383) + string_load(30011),
                         "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    addMenuDirectoryItem(string_load(30383) + string_load(30254), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")
    addMenuDirectoryItem(string_load(30383) + string_load(30395), "plugin://plugin.video.embycon/?mode=CLEAR_CACHE")

    # only add these if we have other collection which means we have a valid server conn
    if collections:
        addMenuDirectoryItem(string_load(30383) + string_load(30293),
                             "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK")
        addMenuDirectoryItem(string_load(30247), "plugin://plugin.video.embycon/?mode=WIDGETS")

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def getCollections():
    log.debug("== ENTER: getCollections ==")

    server = downloadUtils.getServer()
    if server is None:
        return []

    userid = downloadUtils.getUserId()

    if userid is None or len(userid) == 0:
        log.debug("No userid so returning []")
        return []

    data_manager = DataManager()
    result = data_manager.GetContent("{server}/emby/Users/{userid}/Items/Root?format=json")
    if result is None:
        return []

    parentid = result.get("Id")
    log.debug("parentid: {0}", parentid)

    htmlpath = "{server}/emby/Users/{userid}/Views?format=json"
    # htmlpath = "{server}/emby/Users/{userid}/items?ParentId=" + parentid + "&Sortby=SortName&format=json"
    result = data_manager.GetContent(htmlpath)

    if result is not None:
        result = result.get("Items")
    else:
        result = []

    collections = []

    settings = xbmcaddon.Addon()
    group_movies = settings.getSetting('group_movies') == "true"
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    for item in result:
        item_name = item.get("Name")

        collection_type = item.get('CollectionType', None)
        type = item.get('Type', None)
        log.debug("CollectionType: {0}", collection_type)
        log.debug("Title: {0}", item_name)
        art = getArt(item=item, server=server)
        art['landscape'] = downloadUtils.getArtwork(item, "Primary", server=server)

        if collection_type == "music":
            item_data = {}
            item_data['title'] = string_load(30311) + item_name + string_load(30320)
            item_data['art'] = art
            item_data['media_type'] = 'MusicAlbums'
            item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                                 '?Recursive=true' +
                                 '&ParentId=' + item.get("Id") +
                                 '&IncludeItemTypes=MusicAlbum' +
                                 '&ImageTypeLimit=1' +
                                 '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                                 '&SortBy=Name' +
                                 '&SortOrder=Ascending' +
                                 '&format=json')
            collections.append(item_data)

            item_data = {}
            item_data['title'] = string_load(30311) + item_name + string_load(
                30268) + " (" + show_x_filtered_items + ")"
            item_data['art'] = art
            item_data['media_type'] = 'MusicAlbums'
            item_data['path'] = ('{server}/emby/Users/{userid}/Items/Latest' +
                                 '?IncludeItemTypes=Audio' +
                                 '&ParentId=' + item.get("Id") +
                                 '&ImageTypeLimit=1' +
                                 '&Limit={ItemLimit}' +
                                 '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                                 '&SortBy=Name' +
                                 '&SortOrder=Ascending' +
                                 '&format=json')
            collections.append(item_data)

            item_data = {}
            item_data['title'] = string_load(30311) + item_name + string_load(
                30349) + " (" + show_x_filtered_items + ")"
            item_data['art'] = art
            item_data['media_type'] = 'MusicAlbum'
            item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                                 '?SortBy=DatePlayed' +
                                 '&SortOrder=Descending' +
                                 '&IncludeItemTypes=Audio' +
                                 '&Limit={ItemLimit}' +
                                 '&Recursive=true' +
                                 '&ParentId=' + item.get("Id") +
                                 '&ImageTypeLimit=1' +
                                 '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                                 '&Filters=IsPlayed' +
                                 '&format=json')
            collections.append(item_data)

            item_data = {}
            item_data['title'] = string_load(30311) + item_name + string_load(
                30353) + " (" + show_x_filtered_items + ")"
            item_data['art'] = art
            item_data['media_type'] = 'MusicAlbum'
            item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                                 '?SortBy=PlayCount' +
                                 '&SortOrder=Descending' +
                                 '&IncludeItemTypes=Audio' +
                                 '&Limit={ItemLimit}' +
                                 '&Recursive=true' +
                                 '&ParentId=' + item.get("Id") +
                                 '&ImageTypeLimit=1' +
                                 '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                                 '&Filters=IsPlayed' +
                                 '&format=json')
            collections.append(item_data)

            item_data = {}
            item_data['title'] = string_load(30311) + item_name + string_load(30321)
            item_data['art'] = art
            item_data['media_type'] = 'MusicArtists'
            item_data['path'] = ('{server}/emby/Artists/AlbumArtists' +
                                 '?Recursive=true' +
                                 '&ParentId=' + item.get("Id") +
                                 '&ImageTypeLimit=1' +
                                 '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                                 '&SortBy=Name' +
                                 '&SortOrder=Ascending' +
                                 '&format=json')
            collections.append(item_data)

        if collection_type == "livetv":
            collections.append({
                'title': string_load(30311) + item_name + string_load(30360),
                'art': art,
                'path': ('{server}/emby/LiveTv/Channels' +
                         '?UserId={userid}' +
                         '&Recursive=false' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&EnableTotalRecordCount=false' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30361),
                'art': art,
                'path': ('{server}/emby/LiveTv/Programs/Recommended' +
                         '?UserId={userid}' +
                         '&IsAiring=true' +
                         '&Fields=ChannelInfo,{field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&EnableTotalRecordCount=false' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30362),
                'art': art,
                'path': ('{server}/emby/LiveTv/Recordings' +
                         '?UserId={userid}' +
                         '&Recursive=false' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&EnableTotalRecordCount=false' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "musicvideos":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&Recursive=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "homevideos":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&Recursive=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30267) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&SortBy=DatePlayed' +
                         '&SortOrder=Descending' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsResumable' +
                         '&Recursive=true' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30268) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "boxsets":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IncludeItemTypes=Boxset' +
                         '&CollapseBoxSetItems=' + str(group_movies) +
                         '&GroupItemsIntoCollections=' + str(group_movies) +
                         '&Recursive=true' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "playlists":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "tvshows":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30285),
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'tvshows'})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30267) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&SortBy=DatePlayed' +
                         '&SortOrder=Descending' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsResumable' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30288) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items/Latest' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30268) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30278) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30325),
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow&parent_id=' + item.get("Id"),
                'media_type': 'tvshows'})

        if type == "Channel":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'files',
                'name_format': 'Episode|episode_name_format'})

        if collection_type == "movies":
            collections.append({
                'title': string_load(30311) + item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IncludeItemTypes=Movie' +
                         '&CollapseBoxSetItems=' + str(group_movies) +
                         '&GroupItemsIntoCollections=' + str(group_movies) +
                         '&Recursive=true' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30285),
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IncludeItemTypes=Movie' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30267) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IncludeItemTypes=Movie' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&Limit={ItemLimit}' +
                         '&SortBy=DatePlayed' +
                         '&SortOrder=Descending' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsResumable' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30268) + " (" + show_x_filtered_items + ")",
                'art': art,
                'use_cache': False,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IncludeItemTypes=Movie' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30325),
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=GENRES&item_type=movie&parent_id=' + item.get("Id"),
                'media_type': collection_type})

            collections.append({
                'title': string_load(30311) + item_name + string_load(30397),
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=MOVIE_PAGES&parent_id=' + item.get("Id"),
                'media_type': collection_type})

    # Add standard nodes
    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30256)
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&CollapseBoxSetItems=' + str(group_movies) +
                         '&GroupItemsIntoCollections=' + str(group_movies) +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30286)
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30258) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Movies'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?CollapseBoxSetItems=false' +
                         '&Limit={ItemLimit}' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&SortBy=DatePlayed' +
                         '&SortOrder=Descending' +
                         '&Filters=IsResumable' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30257) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Movies'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?CollapseBoxSetItems=false' +
                         '&Limit={ItemLimit}' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30259)
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&Filters=IsFavorite' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30260)
    item_data['media_type'] = 'BoxSets'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&Fields={field_filters}' +
                         '&IncludeItemTypes=BoxSet' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30261)
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30279)
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30262)
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&Filters=IsFavorite' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30287) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Episodes'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Users/{userid}/Items/Latest' +
                         '?GroupItems=true' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed' +
                         '&IsPlayed=false' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30264) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Episodes'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?SortBy=DatePlayed' +
                         '&Limit={ItemLimit}' +
                         '&SortOrder=Descending' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&Filters=IsResumable' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30263) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Episodes'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?SortBy=DateCreated' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30265) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'Episodes'
    item_data['use_cache'] = False
    item_data['path'] = ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsPlayed=false' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30318)
    item_data['media_type'] = 'MusicAlbums'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&IncludeItemTypes=MusicAlbum' +
                         '&ImageTypeLimit=1' +
                         '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30350) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'MusicAlbums'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items/Latest' +
                         '?IncludeItemTypes=Audio' +
                         '&ImageTypeLimit=1' +
                         '&Limit={ItemLimit}' +
                         '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30351) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'MusicAlbum'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?SortBy=DatePlayed' +
                         '&SortOrder=Descending' +
                         '&IncludeItemTypes=Audio' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&ImageTypeLimit=1' +
                         '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                         '&Filters=IsPlayed' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30352) + " (" + show_x_filtered_items + ")"
    item_data['media_type'] = 'MusicAlbum'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?SortBy=PlayCount' +
                         '&SortOrder=Descending' +
                         '&IncludeItemTypes=Audio' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&ImageTypeLimit=1' +
                         '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                         '&Filters=IsPlayed' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = string_load(30312) + string_load(30319)
    item_data['media_type'] = 'MusicArtists'
    item_data['path'] = ('{server}/emby/Artists/AlbumArtists' +
                         '?Recursive=true' +
                         '&ImageTypeLimit=1' +
                         '&EnableImageTypes=Primary,Backdrop,Banner,Thumb' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    return collections




def show_widgets():
    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    addMenuDirectoryItem(string_load(30257) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies')
    addMenuDirectoryItem(string_load(30258) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    addMenuDirectoryItem(string_load(30269) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=random_movies')
    addMenuDirectoryItem(string_load(30403) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=movie_recommendations')

    addMenuDirectoryItem(string_load(30287) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_tvshows')
    addMenuDirectoryItem(string_load(30263) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    addMenuDirectoryItem(string_load(30264) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    addMenuDirectoryItem(string_load(30265) + " (" + show_x_filtered_items + ")",
                         'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_search():
    addMenuDirectoryItem(string_load(30231), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Movie')
    addMenuDirectoryItem(string_load(30229), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Series')
    addMenuDirectoryItem(string_load(30235), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Episode')
    addMenuDirectoryItem(string_load(30337), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Audio')
    addMenuDirectoryItem(string_load(30338), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=MusicAlbum')
    addMenuDirectoryItem(string_load(30339), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Person')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def set_library_window_values(force=False):
    log.debug("set_library_window_values Called forced={0}", force)
    home_window = HomeWindow()

    already_set = home_window.getProperty("view_item.0.name")
    if not force and already_set:
        return

    for index in range(0, 20):
        home_window.clearProperty("view_item.%i.name" % index)
        home_window.clearProperty("view_item.%i.id" % index)
        home_window.clearProperty("view_item.%i.type" % index)
        home_window.clearProperty("view_item.%i.thumb" % index)

    data_manager = DataManager()
    url = "{server}/emby/Users/{userid}/Views"
    result = data_manager.GetContent(url)

    if result is None:
        return

    result = result.get("Items")
    server = downloadUtils.getServer()

    index = 0
    for item in result:

        type = item.get("CollectionType")
        if type in ["movies", "boxsets", "music", "tvshows"]:
            name = item.get("Name")
            id = item.get("Id")

            # plugin.video.embycon-
            prop_name = "view_item.%i.name" % index
            home_window.setProperty(prop_name, name)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, name)

            prop_name = "view_item.%i.id" % index
            home_window.setProperty(prop_name, id)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, id)

            prop_name = "view_item.%i.type" % index
            home_window.setProperty(prop_name, type)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, type)

            thumb = downloadUtils.getArtwork(item, "Primary", server=server)
            prop_name = "view_item.%i.thumb" % index
            home_window.setProperty(prop_name, thumb)
            log.debug("set_library_window_values: plugin.video.embycon-{0}={1}", prop_name, thumb)

            index += 1
