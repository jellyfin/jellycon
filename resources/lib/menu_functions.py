# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import sys
import json
import urllib

import xbmcplugin
import xbmcaddon

from downloadutils import DownloadUtils
from kodi_utils import addMenuDirectoryItem, HomeWindow
from simple_logging import SimpleLogging
from translation import i18n
from datamanager import DataManager
from utils import getArt

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()

__addon__ = xbmcaddon.Addon()

def showMoviePages(params):
    log.debug("showMoviePages: {0}", params)

    parent_id = params.get("parent_id")
    settings = xbmcaddon.Addon()

    group_movies = settings.getSetting('group_movies') == "true"

    url = ('{server}/emby/Users/{userid}/Items' +
           '?IsVirtualUnaired=false' +
           '&CollapseBoxSetItems=' + str(group_movies) +
           '&GroupItemsIntoCollections=' + str(group_movies) +
           '&Recursive=true' +
           "&IncludeItemTypes=Movie"
           '&IsMissing=False' +
           '&ImageTypeLimit=0' +
           '&format=json')

    if parent_id:
        url += "&ParentId=" + parent_id

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

        item_url = ("{server}/emby/Users/{userid}/Items" +
                    "?IsVirtualUnaired=false" +
                    '&CollapseBoxSetItems=' + str(group_movies) +
                    '&GroupItemsIntoCollections=' + str(group_movies) +
                    "&Recursive=true" +
                    "&IsMissing=False" +
                    "&IncludeItemTypes=Movie"
                    "&Fields={field_filters}" +
                    "&ImageTypeLimit=1" +
                    "&SortBy=Name" +
                    "&SortOrder=Ascending" +
                    "&format=json")

        if parent_id:
            item_url += "&ParentId=" + parent_id

        item_url += "&StartIndex=" + str(start_index) + "&Limit=" + str(page_limit)

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
        addMenuDirectoryItem(collection.get('title', i18n('unknown')), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def showGenreList(params):
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

    url = ("{server}/emby/Genres?" +
           "SortBy=Name" +
           "&SortOrder=Ascending" +
           "&IncludeItemTypes=" + emby_type +
           "&Recursive=true" +
           "&UserId={userid}")

    if parent_id is not None:
        url += "&parentid=" + parent_id

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

        url = ("{server}/emby/Users/{userid}/Items" +
               "?Fields={field_filters}" +
               "&Recursive=true" +
               '&CollapseBoxSetItems=' + str(group_movies) +
               '&GroupItemsIntoCollections=' + str(group_movies) +
               "&GenreIds=" + genre.get("Id") +
               "&IncludeItemTypes=" + emby_type +
               "&ImageTypeLimit=1")

        if parent_id is not None:
            url += "&parentid=" + parent_id

        item_data['path'] = url
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + ("?url=" + urllib.quote(collection['path']) +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} - {1} - {2}", collection.get('title'), url, collection.get("art"))
        addMenuDirectoryItem(collection.get('title', i18n('unknown')), url, art=collection.get("art"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def showMovieAlphaList():
    log.debug("== ENTER: showMovieAlphaList() ==")

    settings = xbmcaddon.Addon()
    server = downloadUtils.getServer()
    if server is None:
        return

    collections = []

    item_data = {}
    item_data['title'] = "#"
    item_data['media_type'] = "Movies"
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&NameLessThan=A' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    group_movies = settings.getSetting('group_movies') == "true"
    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['title'] = alphaName
        item_data['media_type'] = "Movies"
        item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                             '?Fields={field_filters}' +
                             '&CollapseBoxSetItems=' + str(group_movies) +
                             '&GroupItemsIntoCollections=' + str(group_movies) +
                             '&Recursive=true' +
                             '&NameStartsWith=' + alphaName +
                             '&IncludeItemTypes=Movie' +
                             "&SortBy=Name" +
                             "&SortOrder=Ascending" +
                             '&ImageTypeLimit=1&format=json')
        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
               "&mode=GET_CONTENT&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        addMenuDirectoryItem(collection.get('title', i18n('unknown')), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


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
                addMenuDirectoryItem(collection.get('title', i18n('unknown')),
                                     plugin_path,
                                     art=collection.get("art"))
            else:
                url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
                       "&mode=GET_CONTENT&media_type=" + collection["media_type"])
                if collection.get("name_format") is not None:
                    url += "&name_format=" + urllib.quote(collection.get("name_format"))
                log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
                addMenuDirectoryItem(collection.get('title', i18n('unknown')),
                                     url,
                                     art=collection.get("art"))

        addMenuDirectoryItem(i18n('movies_genre'), "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie")
        addMenuDirectoryItem(i18n('movies_az'), "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA")
        addMenuDirectoryItem("Movie (Pages)", "plugin://plugin.video.embycon/?mode=MOVIE_PAGES")

        addMenuDirectoryItem(i18n('tvshow_genre'), "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow")
        addMenuDirectoryItem(i18n('search'), "plugin://plugin.video.embycon/?mode=SEARCH")

        addMenuDirectoryItem(i18n('show_clients'), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
        addMenuDirectoryItem(i18n('change_user'), "plugin://plugin.video.embycon/?mode=CHANGE_USER")

    addMenuDirectoryItem(i18n('detect_server'), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    addMenuDirectoryItem(i18n('show_settings'), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")

    # only add these if we have other collection which means we have a valid server conn
    if collections:
        addMenuDirectoryItem(i18n('cache_textures'), "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK")
        addMenuDirectoryItem(i18n('widgets'), "plugin://plugin.video.embycon/?mode=WIDGETS")

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
            item_data['title'] = item_name + i18n('_all_albums')
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
            item_data['title'] = item_name + i18n('_all_artists')
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

        if collection_type in ["homevideos"]:
            collections.append({
                'title': item_name,
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

        if collection_type in ["boxsets"]:
            collections.append({
                'title': item_name,
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

        if collection_type in ["movies"]:
            collections.append({
                'title': item_name,
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

        if collection_type == "tvshows":
            collections.append({
                'title': item_name,
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})
            collections.append({
                'title': item_name + i18n('_unwatched'),
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'tvshows'})
            collections.append({
                'title': item_name + i18n('_in_progress'),
                'art': art,
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
                'title': item_name + i18n('_latest'),
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items/Latest' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})
            collections.append({
                'title': item_name + i18n('_recently_added'),
                'art': art,
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields={field_filters}' +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters={IsUnplayed,}IsNotFolder' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})
            collections.append({
                'title': item_name + i18n('_next_up'),
                'art': art,
                'path': ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'Episode|episode_name_format'})
            collections.append({
                'title': item_name + i18n('_genres'),
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow&parent_id=' + item.get("Id"),
                'media_type': 'tvshows'})

        if type == "Channel":
            collections.append({
                'title': item_name,
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
                'title': item_name + i18n('_unwatched'),
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
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json'),
                'media_type': collection_type})
            collections.append({
                'title': item_name + i18n('_in_progress'),
                'art': art,
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
                'title': item_name + i18n('_recently_added'),
                'art': art,
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
                         '&Filters={IsUnplayed,}IsNotFolder' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})
            collections.append({
                'title': item_name + i18n('_genres'),
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=GENRES&item_type=movie&parent_id=' + item.get("Id"),
                'media_type': collection_type})
            collections.append({
                'title': item_name + ' - Pages',
                'item_type': 'plugin_link',
                'art': art,
                'path': 'plugin://plugin.video.embycon/?mode=MOVIE_PAGES&parent_id=' + item.get("Id"),
                'media_type': collection_type})


    # Add standard nodes
    item_data = {}
    item_data['title'] = i18n('movies_all')
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
    item_data['title'] = i18n('movies_unwatched')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_in_progress')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&CollapseBoxSetItems=false' +
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
    item_data['title'] = i18n('movies_recently_added')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&CollapseBoxSetItems=false' +
                         '&GroupItemsIntoCollections=false' +
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters={IsUnplayed,}IsNotFolder' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_favorites')
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
    item_data['title'] = i18n('movies_boxsets')
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
    item_data['title'] = i18n('tvshows_all')
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
    item_data['title'] = i18n('tvshows_unwatched')
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&Filters=IsUnplayed' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('tvshows_favorites')
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
    item_data['title'] = i18n('tvshows_latest')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items/Latest' +
                         '?Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&GroupItems=true' +
                         '&SortBy=DateCreated' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters={IsUnplayed}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('episodes_in_progress')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&SortBy=DatePlayed' +
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
    item_data['title'] = i18n('episodes_recently_added')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Descending' +
                         '&Filters={IsUnplayed,}IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('episodes_up_next')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields={field_filters}' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'Episode|episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('upcoming_tv')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&SortBy=PremiereDate' +
                         '&Fields={field_filters}' +
                         '&SortOrder=Ascending' +
                         '&IsVirtualUnaired=true' +
                         '&IsNotFolder' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('music_all_albums')
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
    item_data['title'] = i18n('music_all_artists')
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


def showWidgets():

    url = ("{server}/emby/Movies/Recommendations" +
           "?userId={userid}" +
           "&categoryLimit=1" +
           "&ItemLimit={ItemLimit}" +
           "&format=json" +
           "&ImageTypeLimit=1" +
           '&Fields={field_filters}' +
           "&IsMissing=False")
    addMenuDirectoryItem(i18n('movies_recommendations'),
                         "plugin://plugin.video.embycon/?mode=GET_CONTENT&media_type=Movies&url=" + urllib.quote(url))

    url = ("{server}/emby/Users/{userid}/Items" +
           "?Limit={ItemLimit}" +
           '&CollapseBoxSetItems=false' +
           '&GroupItemsIntoCollections=false' +
           "&format=json" +
           '&Fields={field_filters}' +
           "&ImageTypeLimit=1" +
           "&IsMissing=False" +
           "&Filters={IsUnplayed,}IsNotFolder" +
           "&Recursive=true" +
           "&SortBy=Random" +
           "&SortOrder=Descending" +
           "&IsVirtualUnaired=false" +
           "&IsMissing=False" +
           "&IncludeItemTypes=Movie")
    addMenuDirectoryItem(i18n('movies_random'),
                         "plugin://plugin.video.embycon/?mode=GET_CONTENT&media_type=Movies&url=" + urllib.quote(url))

    #addMenuDirectoryItem(i18n('movies_recently_added'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies')
    #addMenuDirectoryItem(i18n('movies_in_progress'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    #addMenuDirectoryItem(i18n('episodes_recently_added'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    #addMenuDirectoryItem(i18n('episodes_in_progress'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    #addMenuDirectoryItem(i18n('episodes_up_next'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def show_search():
    addMenuDirectoryItem(i18n('movies'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Movie')
    addMenuDirectoryItem(i18n('tvshows'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Series')
    addMenuDirectoryItem(i18n('episodes'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Episode')
    addMenuDirectoryItem(i18n('song'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Audio')
    addMenuDirectoryItem(i18n('album'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=MusicAlbum')
    addMenuDirectoryItem(i18n('person'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Person')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def set_library_window_values():
    log.debug("set_library_window_values called")
    home_window = HomeWindow()

    already_set = home_window.getProperty("view_item.0.name")
    if already_set:
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

