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
from .utils import getArt

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
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url, art=collection.get("art"))

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
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url, art=collection.get("art"))

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
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def showTvShowAlphaList():
    log.debug("== ENTER: showTvShowAlphaList() ==")

    settings = xbmcaddon.Addon()
    server = downloadUtils.getServer()
    if server is None:
        return

    collections = []

    item_data = {}
    item_data['title'] = "#"
    item_data['media_type'] = "tvshows"
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields={field_filters}' +
                         '&Recursive=true' +
                         '&NameLessThan=A' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&SortBy=Name' +
                         '&SortOrder=Ascending' +
                         '&format=json')
    collections.append(item_data)

    group_movies = settings.getSetting('group_movies') == "true"
    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['title'] = alphaName
        item_data['media_type'] = "tvshows"
        item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                             '?Fields={field_filters}' +
                             '&Recursive=true' +
                             '&NameStartsWith=' + alphaName +
                             '&IncludeItemTypes=Series' +
                             '&ImageTypeLimit=1' +
                             '&SortBy=Name' +
                             '&SortOrder=Ascending' +
                             '&format=json')
        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
               "&mode=GET_CONTENT&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: {0} ({1})", collection.get('title'), url)
        addMenuDirectoryItem(collection.get('title', string_load(30250)), url)

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

        addMenuDirectoryItem(string_load(30312) + string_load(30251), "plugin://plugin.video.embycon/?mode=GENRES&item_type=movie")
        addMenuDirectoryItem(string_load(30312) + string_load(30252), "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA")
        addMenuDirectoryItem(string_load(30312) + string_load(30266), "plugin://plugin.video.embycon/?mode=MOVIE_PAGES")

        addMenuDirectoryItem(string_load(30312) + string_load(30289), "plugin://plugin.video.embycon/?mode=GENRES&item_type=tvshow")
        addMenuDirectoryItem(string_load(30312) + string_load(30255), "plugin://plugin.video.embycon/?mode=TVSHOW_ALPHA")

        addMenuDirectoryItem(string_load(30383) + string_load(30246), "plugin://plugin.video.embycon/?mode=SEARCH")
        addMenuDirectoryItem(string_load(30383) + string_load(30017), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
        addMenuDirectoryItem(string_load(30383) + string_load(30012), "plugin://plugin.video.embycon/?mode=CHANGE_USER")

    addMenuDirectoryItem(string_load(30383) + string_load(30011), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    addMenuDirectoryItem(string_load(30383) + string_load(30254), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")
    addMenuDirectoryItem(string_load(30383) + string_load(30395), "plugin://plugin.video.embycon/?mode=CLEAR_CACHE")

    # only add these if we have other collection which means we have a valid server conn
    if collections:
        addMenuDirectoryItem(string_load(30383) + string_load(30293), "plugin://plugin.video.embycon/?mode=CACHE_ARTWORK")
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
            item_data['title'] = string_load(30311) + item_name + string_load(30268) + " (" + show_x_filtered_items + ")"
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
            item_data['title'] = string_load(30311) + item_name + string_load(30349) + " (" + show_x_filtered_items + ")"
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
            item_data['title'] = string_load(30311) + item_name + string_load(30353) + " (" + show_x_filtered_items + ")"
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


def showWidgets():

    settings = xbmcaddon.Addon()
    show_x_filtered_items = settings.getSetting("show_x_filtered_items")

    url = ("{server}/emby/Movies/Recommendations" +
           "?userId={userid}" +
           "&categoryLimit=1" +
           "&ItemLimit={ItemLimit}" +
           "&format=json" +
           "&ImageTypeLimit=1" +
           "&Fields={field_filters}" +
           "&Filters=IsUnplayed" +
           "&IsPlayed=false" +
           "&IsMissing=False")
    addMenuDirectoryItem(string_load(30324) + " (" + show_x_filtered_items + ")",
                         "plugin://plugin.video.embycon/?mode=GET_CONTENT&use_cache=false&media_type=Movies&url=" + urllib.quote(url))

    url = ("{server}/emby/Users/{userid}/Items" +
           "?Limit={ItemLimit}" +
           "&Ids={random_movies}" +
           "&Fields={field_filters}" +
           "&ImageTypeLimit=1")
    addMenuDirectoryItem(string_load(30269) + " (" + show_x_filtered_items + ")",
                         "plugin://plugin.video.embycon/?mode=GET_CONTENT&use_cache=false&media_type=Movies&url=" + urllib.quote(url))

    addMenuDirectoryItem(" - " + string_load(30257) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies')
    addMenuDirectoryItem(" - " + string_load(30258) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    addMenuDirectoryItem(" - " + string_load(30269) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=random_movies')
    addMenuDirectoryItem(" - " + string_load(30403) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=movie_recommendations')

    addMenuDirectoryItem(" - " + string_load(30287) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_tvshows')
    addMenuDirectoryItem(" - " + string_load(30263) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    addMenuDirectoryItem(" - " + string_load(30264) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    addMenuDirectoryItem(" - " + string_load(30265) + " (" + show_x_filtered_items + ")", 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

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

