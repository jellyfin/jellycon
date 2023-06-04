from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import sys
import base64
import string

import xbmcplugin
import xbmcaddon
from six import ensure_binary, ensure_text
from six.moves.urllib.parse import quote

from .dir_functions import get_content
from .jellyfin import api
from .kodi_utils import add_menu_directory_item, HomeWindow
from .lazylogger import LazyLogger
from .utils import (
    get_jellyfin_url, translate_string, get_art_url,
    get_default_filters, get_current_user_id
)
from .item_functions import get_art

log = LazyLogger(__name__)

__addon__ = xbmcaddon.Addon()
settings = xbmcaddon.Addon()


def show_movie_tags(menu_params):
    log.debug("show_movie_tags: {0}".format(menu_params))
    parent_id = menu_params.get("parent_id")
    user_id = get_current_user_id()

    url_params = {
        "UserId": user_id,
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "CollapseBoxSetItems": False,
        "GroupItemsIntoCollections": False,
        "Recursive": True,
        "IsMissing": False,
        "EnableTotalRecordCount": False,
        "EnableUserData": False,
        "IncludeItemTypes": "Movie"
    }

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_jellyfin_url("/Tags", url_params)
    result = api.get(url)

    if not result:
        return

    tags = result.get("Items", [])

    log.debug("Tags : {0}".format(result))

    url_params = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": False,
        "GroupItemsIntoCollections": False,
        "Recursive": True,
        "IsMissing": False,
        "ImageTypeLimit": 1,
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "Fields": get_default_filters()
    }

    for tag in tags:
        name = tag["Name"]
        tag_id = tag["Id"]

        url_params["TagIds"] = tag_id

        if parent_id:
            menu_params["ParentId"] = parent_id

        item_url = get_jellyfin_url("/Users/{userid}/Items", url_params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(item_url))))}

        content_url = quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}".format(name, url))
        add_menu_directory_item(name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_years(menu_params):
    log.debug("show_movie_years: {0}".format(menu_params))
    parent_id = menu_params.get("parent_id")
    group_into_decades = menu_params.get("group") == "true"
    user_id = get_current_user_id()

    url_params = {
        "UserId": user_id,
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "CollapseBoxSetItems": False,
        "GroupItemsIntoCollections": False,
        "Recursive": True,
        "IsMissing": False,
        "EnableTotalRecordCount": False,
        "EnableUserData": False,
        "IncludeItemTypes": "Movie"
    }

    if parent_id:
        url_params["ParentId"] = parent_id

    url = get_jellyfin_url("/Years", url_params)

    result = api.get(url)

    if not result:
        return

    years_list = result.get("Items", [])
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

    params = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": False,
        "GroupItemsIntoCollections": False,
        "Recursive": True,
        "IsMissing": False,
        "ImageTypeLimit": 1,
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "Fields": get_default_filters()
    }

    for year in keys:
        name = year
        value = ",".join(result_names[year])

        params["Years"] = value

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(item_url))))}

        content_url = quote(item_url)
        url = sys.argv[0] + ("?url=" +
                             content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1}".format(name, url))
        add_menu_directory_item(name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_pages(menu_params):
    log.debug("showMoviePages: {0}".format(menu_params))

    parent_id = menu_params.get("parent_id")
    group_movies = settings.getSetting('group_movies') == "true"
    user_id = get_current_user_id()

    params = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": group_movies,
        "GroupItemsIntoCollections": group_movies,
        "Recursive": True,
        "IsMissing": False,
        "ImageTypeLimit": 0
    }

    if parent_id:
        params["ParentId"] = parent_id

    url = get_jellyfin_url("/Users/{}/Items".format(user_id), params)

    result = api.get(url)

    if result is None:
        return

    total_results = result.get("TotalRecordCount", 0)
    log.debug("showMoviePages TotalRecordCount {0}".format(total_results))

    if result == 0:
        return

    page_limit = int(settings.getSetting('moviePageSize'))
    if page_limit == 0:
        page_limit = 20

    start_index = 0

    params = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": group_movies,
        "GroupItemsIntoCollections": group_movies,
        "Recursive": True,
        "IsMissing": False,
        "ImageTypeLimit": 1,
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "Fields": get_default_filters()
    }

    while start_index < total_results:

        params["StartIndex"] = start_index
        params["Limit"] = page_limit

        if parent_id:
            params["ParentId"] = parent_id

        item_url = get_jellyfin_url("/Users/{userid}/Items", params)

        page_upper = start_index + page_limit
        if page_upper > total_results:
            page_upper = total_results

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(item_url))))}
        title = 'Page ({} - {})'.format(start_index + 1, page_upper)

        start_index = start_index + page_limit

        content_url = quote(item_url)
        url = sys.argv[0] + ("?url=" + content_url +
                             "&mode=GET_CONTENT" +
                             "&media_type=movies")
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}".format(title, url, art))
        add_menu_directory_item(title, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_genre_list(menu_params):
    log.debug("showGenreList: {0}".format(menu_params))

    server = settings.getSetting('server_address')
    if server is None:
        return

    parent_id = menu_params.get("parent_id")
    item_type = menu_params.get("item_type")
    user_id = get_current_user_id()

    jellyfin_type = ''
    kodi_type = ''
    if item_type == 'movie':
        jellyfin_type = "Movie"
        kodi_type = 'Movies'
    elif item_type == 'tvshow':
        jellyfin_type = 'Series'
        kodi_type = 'tvshows'
    elif item_type == 'MusicAlbum':
        jellyfin_type = 'MusicAlbum'
        kodi_type = 'albums'
    elif item_type == 'mixed':
        jellyfin_type = 'Movie,Series'
        kodi_type = 'videos'

    params = {
        "IncludeItemTypes": jellyfin_type,
        "UserId": user_id,
        "Recursive": True,
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "ImageTypeLimit": 1
    }

    if parent_id is not None:
        params["ParentId"] = parent_id

    url = get_jellyfin_url("/Genres", params)

    result = api.get(url)

    if result is not None:
        result = result.get("Items")
    else:
        result = []

    group_movies = settings.getSetting('group_movies') == "true"

    xbmcplugin.setContent(int(sys.argv[1]), 'genres')

    params = {
        "Recursive": True,
        "CollapseBoxSetItems": group_movies,
        "GroupItemsIntoCollections": group_movies,
        "IncludeItemTypes": jellyfin_type,
        "ImageTypeLimit": 1,
        "Fields": get_default_filters()
    }

    for genre in result:
        title = genre.get('Name', translate_string(30250))

        genre_id = genre.get("Id")
        params["GenreIds"] = genre_id
        li_properties = {"id": genre_id}

        if parent_id is not None:
            params["ParentId"] = parent_id

        path = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(path))))}

        url = sys.argv[0] + ("?url=" + quote(path) +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + kodi_type)
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}".format(title, url, art))
        add_menu_directory_item(title, url, art=art, properties=li_properties)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_movie_alpha_list(menu_params):
    log.debug("== ENTER: showMovieAlphaList() ==")

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')

    server = settings.getSetting('server_address')
    if server is None:
        return

    group_movies = settings.getSetting('group_movies') == "true"
    parent_id = menu_params.get("parent_id")
    user_id = get_current_user_id()

    url_params = {
        "IncludeItemTypes": "Movie",
        "Recursive": True,
        "GroupItemsIntoCollections": group_movies,
        "UserId": user_id,
        "SortBy": "Name",
        "SortOrder": "Ascending"
    }

    if parent_id is not None:
        url_params["ParentId"] = parent_id

    prefixes = '#' + string.ascii_uppercase

    params = {
        "Fields": get_default_filters(),
        "CollapseBoxSetItems": group_movies,
        "GroupItemsIntoCollections": group_movies,
        "Recursive": True,
        "IncludeItemTypes": "Movie",
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "ImageTypeLimit": 1
    }

    for alpha_name in prefixes:
        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
            # Ensure we don't try to search both at once
            if 'NameStartsWith' in params:
                params.pop('NameStartsWith')
        else:
            params["NameStartsWith"] = alpha_name
            # Ensure we don't try to search both at once
            if 'NameLessThan' in params:
                params.pop('NameLessThan')

        path = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(path))))}

        url = (sys.argv[0] + "?url=" + quote(path) +
               "&mode=GET_CONTENT&media_type=Movies")
        log.debug("addMenuDirectoryItem: {0} ({1})".format(alpha_name, url))
        add_menu_directory_item(alpha_name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_tvshow_alpha_list(menu_params):
    log.debug("== ENTER: showTvShowAlphaList() ==")

    server = settings.getSetting('server_address')
    if server is None:
        return

    parent_id = menu_params.get("parent_id")

    prefixes = '#' + string.ascii_uppercase

    params = {
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Series",
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "Recursive": True,
        "IsMissing": False
    }

    for alpha_name in prefixes:

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
            # Ensure we don't try to search both at once
            if 'NameStartsWith' in params:
                params.pop('NameStartsWith')
        else:
            params["NameStartsWith"] = alpha_name
            # Ensure we don't try to search both at once
            if 'NameLessThan' in params:
                params.pop('NameLessThan')

        path = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(path))))}

        url = (sys.argv[0] + "?url=" + quote(path) +
               "&mode=GET_CONTENT&media_type=tvshows")
        log.debug("addMenuDirectoryItem: {0} ({1})".format(alpha_name, url))
        add_menu_directory_item(alpha_name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_mixed_alpha_list(menu_params):
    log.debug("== ENTER: showTvShowAlphaList() ==")

    server = settings.getSetting('server_address')
    if server is None:
        return

    parent_id = menu_params.get("parent_id")

    prefixes = '#' + string.ascii_uppercase

    params = {
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Series,Movie",
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "Recursive": True,
        "IsMissing": False
    }

    for alpha_name in prefixes:

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
            # Ensure we don't try to search both at once
            if 'NameStartsWith' in params:
                params.pop('NameStartsWith')
        else:
            params["NameStartsWith"] = alpha_name
            # Ensure we don't try to search both at once
            if 'NameLessThan' in params:
                params.pop('NameLessThan')

        path = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(path))))}

        url = (sys.argv[0] + "?url=" + quote(path) +
               "&mode=GET_CONTENT&media_type=mixed")
        log.debug("addMenuDirectoryItem: {0} ({1})".format(alpha_name, url))
        add_menu_directory_item(alpha_name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_artist_alpha_list(menu_params):
    log.debug("== ENTER: showArtistAlphaList() ==")

    xbmcplugin.setContent(int(sys.argv[1]), 'artists')

    server = settings.getSetting('server_address')
    if server is None:
        return

    parent_id = menu_params.get("parent_id")
    user_id = get_current_user_id()

    url_params = {
        "IncludeItemTypes": "MusicArtist",
        "Recursive": True,
        "UserId": user_id,
        "SortBy": "Name",
        "SortOrder": "Ascending"
    }

    if parent_id is not None:
        url_params["ParentId"] = parent_id

    prefixes = '#' + string.ascii_uppercase

    params = {
        "Fields": get_default_filters(),
        "Recursive": True,
        "IncludeItemTypes": "MusicArtist",
        "SortBy": "Name",
        "SortOrder": "Ascending",
        "ImageTypeLimit": 1
    }

    for alpha_name in prefixes:

        if parent_id is not None:
            params["ParentId"] = parent_id

        if alpha_name == "#":
            params["NameLessThan"] = "A"
            # Ensure we don't try to search both at once
            if 'NameStartsWith' in params:
                params.pop('NameStartsWith')
        else:
            params["NameStartsWith"] = alpha_name
            # Ensure we don't try to search both at once
            if 'NameLessThan' in params:
                params.pop('NameLessThan')

        path = get_jellyfin_url("/Users/{userid}/Items", params)

        art = {"thumb": "http://localhost:24276/{}".format(ensure_text(base64.b64encode(ensure_binary(path))))}

        url = (sys.argv[0] + "?url=" + quote(path) +
               "&mode=GET_CONTENT&media_type=Artists")
        log.debug("addMenuDirectoryItem: {0} ({1})".format(alpha_name, url))
        add_menu_directory_item(alpha_name, url, art=art)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def display_main_menu():
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    if settings.getSetting("interface_mode") == "1":
        display_library_views(None)
        return

    add_menu_directory_item(translate_string(30406),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=library")
    add_menu_directory_item(translate_string(30407),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=show_global_types")
    add_menu_directory_item(translate_string(30408),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=show_custom_widgets")
    add_menu_directory_item(translate_string(30409),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=addon_items")

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

    continue_watching_url_params = {
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
    }
    continue_watching_url = get_jellyfin_url("/Users/{userid}/Items/Resume", continue_watching_url_params)
    add_menu_directory_item(translate_string(30445),
                            "plugin://plugin.video.jellycon/?mode=GET_CONTENT&url=" + quote(continue_watching_url) +
                            "&media_type=movies" +
                            "&name_format="+quote("Episode|episode_name_format"))

    add_menu_directory_item(translate_string(30256),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=global_list_movies")
    add_menu_directory_item(translate_string(30261),
                            "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=global_list_tvshows")

    xbmcplugin.endOfDirectory(handle)


def display_homevideos_type(menu_params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")
    item_limit = settings.getSetting("show_x_filtered_items")
    hide_watched = settings.getSetting("hide_watched") == "true"

    # All Home Movies
    base_params = {
        "ParentId": view.get("Id"),
        "Recursive": False,
        "IsMissing": False,
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1
    }
    path = get_jellyfin_url("/Users/{userid}/Items", base_params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + translate_string(30405), url)

    # In progress home movies
    params = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["Recursive"] = True
    params["Limit"] = item_limit
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + translate_string(30267) + " (" + item_limit + ")", url)

    # Recently added
    params = {}
    params.update(base_params)
    params["Recursive"] = True
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    if hide_watched:
        params["IsPlayed"] = False
    params["Limit"] = item_limit
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=homevideos"
    add_menu_directory_item(view_name + translate_string(30268) + " (" + item_limit + ")", url)

    xbmcplugin.endOfDirectory(handle)


def display_addon_menu(params):

    add_menu_directory_item(translate_string(30246), "plugin://plugin.video.jellycon/?mode=SEARCH")
    add_menu_directory_item(translate_string(30017), "plugin://plugin.video.jellycon/?mode=SHOW_SERVER_SESSIONS")
    add_menu_directory_item(translate_string(30012), "plugin://plugin.video.jellycon/?mode=CHANGE_USER")
    add_menu_directory_item(translate_string(30011), "plugin://plugin.video.jellycon/?mode=DETECT_SERVER_USER")
    add_menu_directory_item(translate_string(30435), "plugin://plugin.video.jellycon/?mode=DETECT_CONNECTION_SPEED")
    add_menu_directory_item(translate_string(30254), "plugin://plugin.video.jellycon/?mode=SHOW_SETTINGS")
    add_menu_directory_item(translate_string(30395), "plugin://plugin.video.jellycon/?mode=CLEAR_CACHE")
    add_menu_directory_item(translate_string(30293), "plugin://plugin.video.jellycon/?mode=CACHE_ARTWORK")
    add_menu_directory_item("Clone default skin", "plugin://plugin.video.jellycon/?mode=CLONE_SKIN")

    handle = int(sys.argv[1])
    xbmcplugin.endOfDirectory(handle)


def display_tvshow_type(menu_params, view):
    handle = int(sys.argv[1])

    view_name = translate_string(30261)
    if view is not None:
        view_name = view.get("Name")

    item_limit = settings.getSetting("show_x_filtered_items")

    # All TV Shows
    base_params = {
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
        "IsMissing": False,
        "IncludeItemTypes": "Series",
        "Recursive": True
    }
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    path = get_jellyfin_url("/Users/{userid}/Items", base_params)

    if settings.getSetting("interface_mode") == "1":
        get_content(path, { "media_type": "tvshows" })
        return

    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + translate_string(30405), url)

    # Favorite TV Shows
    params = {}
    params.update(base_params)
    params["Filters"] = "IsFavorite"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + translate_string(30414), url)

    # Tv Shows with unplayed
    params = {}
    params.update(base_params)
    params["IsPlayed"] = False
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=tvshows"
    add_menu_directory_item(view_name + translate_string(30285), url)

    # In progress episodes
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsResumable"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30267) + " (" + item_limit + ")", url)

    # Latest Episodes
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=tvshows&sort=none"
    add_menu_directory_item(view_name + translate_string(30288) + " (" + item_limit + ")", url)

    # Recently Added
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30268) + " (" + item_limit + ")", url)

    # Next Up Episodes
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["Userid"] = '{userid}'
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Shows/NextUp", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30278) + " (" + item_limit + ")", url)

    # TV Show Genres
    path = "plugin://plugin.video.jellycon/?mode=GENRES&item_type=tvshow"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + translate_string(30325), path)

    # TV Show Alpha picker
    path = "plugin://plugin.video.jellycon/?mode=TVSHOW_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + translate_string(30404), path)

    xbmcplugin.endOfDirectory(handle)


def display_music_type(menu_params, view):
    handle = int(sys.argv[1])
    view_name = view.get("Name")

    item_limit = settings.getSetting("show_x_filtered_items")

    # all albums
    params = {
        "ParentId": view.get("Id"),
        "Recursive": True,
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "MusicAlbum"
    }
    path = get_jellyfin_url("/Users/{userid}/Items", params)

    if settings.getSetting("interface_mode") == "1":
        get_content(path, { "media_type": "MusicAlbums" })
        return

    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    add_menu_directory_item(view_name + translate_string(30320), url)

    # recently added
    params = {
        "ParentId": view.get("Id"),
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Audio",
        "Limit": item_limit
    }
    path = get_jellyfin_url("/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbums"
    add_menu_directory_item(view_name + translate_string(30268) + " (" + item_limit + ")", url)

    # recently played
    params = {
        "ParentId": view.get("Id"),
        "Recursive": True,
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Audio",
        "Limit": item_limit,
        "IsPlayed": True,
        "SortBy": "DatePlayed",
        "SortOrder": "Descending"
    }
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    add_menu_directory_item(view_name + translate_string(30349) + " (" + item_limit + ")", url)

    # most played
    params = {
        "ParentId": view.get("Id"),
        "Recursive": True,
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Audio",
        "Limit": item_limit,
        "IsPlayed": True,
        "SortBy": "PlayCount",
        "SortOrder": "Descending"
    }
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=MusicAlbum"
    add_menu_directory_item(view_name + translate_string(30353) + " (" + item_limit + ")", url)

    # artists
    params = {
        "ParentId": view.get("Id"),
        "Recursive": True,
        "ImageTypeLimit": 1
    }
    path = get_jellyfin_url("/Artists/AlbumArtists", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=MusicArtists"
    add_menu_directory_item(view_name + translate_string(30321), url)

    # genres
    path = "plugin://plugin.video.jellycon/?mode=GENRES&item_type=MusicAlbum"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + translate_string(30325), path)

    # Artist Alpha picker
    path = "plugin://plugin.video.jellycon/?mode=ARTIST_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{} - {}{}'.format(
        view_name, translate_string(30323), translate_string(30404)), path)

    # Shuffle All
    path = "plugin://plugin.video.jellycon/?mode=PLAY&action=shuffle"
    if view is not None:
        path += "&item_id=" + view.get("Id")
    add_menu_directory_item('{} - {}'.format(
        view_name, translate_string(30448)), path, False)

    xbmcplugin.endOfDirectory(handle)


def display_musicvideos_type(params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    # artists
    params = {
        "ParentId": view.get("Id"),
        "Recursive": False,
        "ImageTypeLimit": 1,
        "IsMissing": False,
        "Fields": get_default_filters()
    }
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=musicvideos"
    add_menu_directory_item(view_name + translate_string(30405), url)

    xbmcplugin.endOfDirectory(handle)


def display_livetv_type(menu_params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = view.get("Name")

    # channels
    params = {
        "UserId": '{userid}',
        "Recursive": False,
        "ImageTypeLimit": 1,
        "Fields": get_default_filters()
    }
    path = get_jellyfin_url("/LiveTv/Channels", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + translate_string(30360), url)

    # programs
    params = {
        "UserId": '{userid}',
        "IsAiring": True,
        "ImageTypeLimit": 1,
        "Fields": get_default_filters() + ",ChannelInfo",
        "EnableTotalRecordCount": False
    }
    path = get_jellyfin_url("/LiveTv/Programs/Recommended", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + translate_string(30361), url)

    # recordings
    params = {
        "UserId": '{userid}',
        "Recursive": False,
        "ImageTypeLimit": 1,
        "Fields": get_default_filters(),
        "EnableTotalRecordCount": False
    }
    path = get_jellyfin_url("/LiveTv/Recordings", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=livetv"
    add_menu_directory_item(view_name + translate_string(30362), url)

    xbmcplugin.endOfDirectory(handle)


def display_movies_type(menu_params, view):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    view_name = translate_string(30256)
    if view is not None:
        view_name = view.get("Name")

    item_limit = settings.getSetting("show_x_filtered_items")
    group_movies = settings.getSetting('group_movies') == "true"
    hide_watched = settings.getSetting("hide_watched") == "true"

    base_params = {
        "IncludeItemTypes": "Movie",
        "CollapseBoxSetItems": group_movies,
        "GroupItemsIntoCollections": group_movies,
        "Recursive": True,
        "IsMissing": False,
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1
    }
    if view is not None:
        base_params["ParentId"] = view.get("Id")

    # All Movies
    path = get_jellyfin_url("/Users/{userid}/Items", base_params)

    if settings.getSetting("interface_mode") == "1":
        get_content(path, { "media_type": "movies" })
        return

    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30405)), url)

    # Favorite Movies
    params = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["Filters"] = "IsFavorite"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30414)), url)

    # Unwatched Movies
    params = {}
    params.update(base_params)
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["IsPlayed"] = False
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies"
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30285)), url)

    # Recently Watched Movies
    params = {}
    params.update(base_params)
    params["IsPlayed"] = True
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["CollapseBoxSetItems"] = False
    params["GroupItemsIntoCollections"] = False
    params["Limit"] = item_limit
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item('{}{} ({})'.format(view_name, translate_string(30349), item_limit), url)

    # Resumable Movies
    params = {}
    params.update(base_params)
    params["Filters"] = "IsResumable"
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Limit"] = item_limit
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item('{}{} ({})'.format(view_name, translate_string(30267), item_limit), url)

    # Recently Added Movies
    params = {}
    params.update(base_params)
    if hide_watched:
        params["IsPlayed"] = False
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["Limit"] = item_limit
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=movies&sort=none"
    add_menu_directory_item('{}{} ({})'.format(view_name, translate_string(30268), item_limit), url)

    # Collections
    params = {}
    if view is not None:
        params["ParentId"] = view.get("Id")
    params["Fields"] = get_default_filters()
    params["ImageTypeLimit"] = 1
    params["IncludeItemTypes"] = "Boxset"
    params["Recursive"] = True
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30410)), url)

    # Favorite Collections
    params["Filters"] = "IsFavorite"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30415)), url)

    # Genres
    path = "plugin://plugin.video.jellycon/?mode=GENRES&item_type=movie"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30325)), path)

    # Pages
    path = "plugin://plugin.video.jellycon/?mode=MOVIE_PAGES"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30397)), path)

    # Alpha Picker
    path = "plugin://plugin.video.jellycon/?mode=MOVIE_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30404)), path)

    # Years
    path = "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=show_movie_years"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30411)), path)

    # Decades
    path = "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=show_movie_years&group=true"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30412)), path)

    # Tags
    path = "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=show_movie_tags"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item('{}{}'.format(view_name, translate_string(30413)), path)

    xbmcplugin.endOfDirectory(handle)


def display_mixed_type(params, view):
    handle = int(sys.argv[1])

    view_name = translate_string(30261)
    if view is not None:
        view_name = view.get("Name")

    item_limit = settings.getSetting("show_x_filtered_items")

    # All Mixed content
    base_params = {
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
        "IsMissing": False,
        "IncludeItemTypes": "Series,Movie",
        "Recursive": True
    }
    if view is not None:
        base_params["ParentId"] = view.get("Id")
    path = get_jellyfin_url("/Users/{userid}/Items", base_params)

    if settings.getSetting("interface_mode") == "1":
        get_content(path, { "media_type": "mixed" })
        return

    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed"
    add_menu_directory_item(view_name + translate_string(30405), url)

    # Favorite Mixed
    params = {}
    params.update(base_params)
    params["Filters"] = "IsFavorite"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed"
    add_menu_directory_item(view_name + translate_string(30414), url)

    # Unplayed Mixed
    params = {}
    params.update(base_params)
    params["IsPlayed"] = False
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed"
    add_menu_directory_item(view_name + translate_string(30285), url)

    # In progress mixed
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DatePlayed"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsResumable"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30267) + " (" + item_limit + ")", url)

    # Latest mixed
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items/Latest", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed&sort=none"
    add_menu_directory_item(view_name + translate_string(30288) + " (" + item_limit + ")", url)

    # Recently Added
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=mixed&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30268) + " (" + item_limit + ")", url)

    # Next Up Episodes
    params = {}
    params.update(base_params)
    params["Limit"] = item_limit
    params["Userid"] = '{userid}'
    params["SortBy"] = "DateCreated"
    params["SortOrder"] = "Descending"
    params["Filters"] = "IsNotFolder"
    params["IncludeItemTypes"] = "Episode"
    path = get_jellyfin_url("/Shows/NextUp", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=Episodes&sort=none"
    url += "&name_format=" + quote('Episode|episode_name_format')
    add_menu_directory_item(view_name + translate_string(30278) + " (" + item_limit + ")", url)

    # Mixed Genres
    path = "plugin://plugin.video.jellycon/?mode=GENRES&item_type=mixed"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + translate_string(30325), path)

    # Mixed Alpha picker
    path = "plugin://plugin.video.jellycon/?mode=TVSHOW_ALPHA"
    if view is not None:
        path += "&parent_id=" + view.get("Id")
    add_menu_directory_item(view_name + translate_string(30404), path)

    xbmcplugin.endOfDirectory(handle)


def display_library_views(params):
    handle = int(sys.argv[1])
    xbmcplugin.setContent(handle, 'files')

    server = settings.getSetting('server_address')
    if server is None:
        return
    user_id = get_current_user_id()

    views_url = "/Users/{}/Views?format=json".format(user_id)
    views = api.get(views_url)
    if not views:
        return []
    views = views.get("Items", [])

    view_types = ["movies", "tvshows", "homevideos", "boxsets", "playlists", "music", "musicvideos", "livetv", "Channel", "mixed"]

    for view in views:
        collection_type = view.get('CollectionType', 'mixed')
        item_type = view.get('Type', None)
        if collection_type in view_types or item_type == "Channel":
            view_name = view.get("Name")
            art = get_art(item=view, server=server)
            art['landscape'] = get_art_url(view, "Primary", server=server)

            plugin_path = "plugin://plugin.video.jellycon/?mode=SHOW_ADDON_MENU&type=library_item&view_id=" + view.get("Id")

            if collection_type == "playlists":
                plugin_path = get_playlist_path(view)
            elif collection_type == "boxsets":
                plugin_path = get_collection_path(view)
            elif collection_type is None and view.get('Type', None) == "Channel":
                plugin_path = get_channel_path(view)

            add_menu_directory_item(view_name, plugin_path, art=art)

    xbmcplugin.endOfDirectory(handle)


def get_playlist_path(view_info):
    params = {
        "ParentId": view_info.get("Id"),
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1
    }

    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=playlists"
    return url


def get_collection_path(view_info):
    params = {
        "ParentId": view_info.get("Id"),
        "Fields": get_default_filters(),
        "ImageTypeLimit": 1,
        "IncludeItemTypes": "Boxset",
        "CollapseBoxSetItems": True,
        "GroupItemsIntoCollections": True,
        "Recursive": True,
        "IsMissing": False
    }

    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=boxsets"
    return url


def get_channel_path(view):
    params = {
        "ParentId": view.get("Id"),
        "IsMissing": False,
        "ImageTypeLimit": 1,
        "Fields": get_default_filters()
    }

    path = get_jellyfin_url("/Users/{userid}/Items", params)
    url = sys.argv[0] + "?url=" + quote(path) + "&mode=GET_CONTENT&media_type=files"
    return url


def display_library_view(params):
    node_id = params.get("view_id")
    user_id = get_current_user_id()

    view_info_url = "/Users/{}/Items/".format(user_id) + node_id
    view_info = api.get(view_info_url)

    log.debug("VIEW_INFO : {0}".format(view_info))

    collection_type = view_info.get("CollectionType", "mixed")

    if collection_type == "movies":
        display_movies_type(params, view_info)
    elif collection_type == "tvshows":
        display_tvshow_type(params, view_info)
    elif collection_type == "homevideos":
        display_homevideos_type(params, view_info)
    elif collection_type == "music":
        display_music_type(params, view_info)
    elif collection_type == "musicvideos":
        display_musicvideos_type(params, view_info)
    elif collection_type == "livetv":
        display_livetv_type(params, view_info)
    elif collection_type == "mixed":
        display_mixed_type(params, view_info)


def show_widgets():
    item_limit = settings.getSetting("show_x_filtered_items")

    add_menu_directory_item("All Movies",
                            'plugin://plugin.video.jellycon/library/movies')

    add_menu_directory_item(translate_string(30257) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=recent_movies')
    add_menu_directory_item(translate_string(30258) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    add_menu_directory_item(translate_string(30269) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=random_movies')
    add_menu_directory_item(translate_string(30403) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=movie_recommendations')

    add_menu_directory_item(translate_string(30287) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=recent_tvshows')
    add_menu_directory_item(translate_string(30263) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    add_menu_directory_item(translate_string(30264) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    add_menu_directory_item(translate_string(30265) + " (" + item_limit + ")",
                            'plugin://plugin.video.jellycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_search():
    add_menu_directory_item(translate_string(30231), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=Movie')
    add_menu_directory_item(translate_string(30229), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=Series')
    add_menu_directory_item(translate_string(30235), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=Episode')
    add_menu_directory_item(translate_string(30337), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=Audio')
    add_menu_directory_item(translate_string(30338), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=MusicAlbum')
    add_menu_directory_item(translate_string(30339), 'plugin://plugin.video.jellycon/?mode=NEW_SEARCH&item_type=Person')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def set_library_window_values(force=False):
    log.debug("set_library_window_values Called forced={0}".format(force))
    home_window = HomeWindow()

    already_set = home_window.get_property("view_item.0.name")
    if not force and already_set:
        return
    user_id = get_current_user_id()

    for index in range(0, 20):
        home_window.clear_property("view_item.%i.name" % index)
        home_window.clear_property("view_item.%i.id" % index)
        home_window.clear_property("view_item.%i.type" % index)
        home_window.clear_property("view_item.%i.thumb" % index)

    url = "/Users/{}/Views".format(user_id)
    result = api.get(url)

    if result is None:
        return

    result = result.get("Items", [])
    server = settings.getSetting('server_address')

    index = 0
    for item in result:

        collection_type = item.get("CollectionType", "mixed")
        if collection_type in ["movies", "boxsets", "music", "tvshows", "mixed"]:
            name = item.get("Name")
            item_id = item.get("Id")

            # plugin.video.jellycon-
            prop_name = "view_item.%i.name" % index
            home_window.set_property(prop_name, name)
            log.debug("set_library_window_values: plugin.video.jellycon-{0}={1}".format(prop_name, name))

            prop_name = "view_item.%i.id" % index
            home_window.set_property(prop_name, item_id)
            log.debug("set_library_window_values: plugin.video.jellycon-{0}={1}".format(prop_name, item_id))

            prop_name = "view_item.%i.type" % index
            home_window.set_property(prop_name, collection_type)
            log.debug("set_library_window_values: plugin.video.jellycon-{0}={1}".format(prop_name, collection_type))

            thumb = get_art_url(item, "Primary", server=server)
            prop_name = "view_item.%i.thumb" % index
            home_window.set_property(prop_name, thumb)
            log.debug("set_library_window_values: plugin.video.jellycon-{0}={1}".format(prop_name, thumb))

            index += 1
