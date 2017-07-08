# Gnu General Public License - see LICENSE.TXT

import sys
import json
import urllib

import xbmcplugin
import xbmcaddon

from downloadutils import DownloadUtils
from utils import getDetailsString
from kodi_utils import addMenuDirectoryItem
from simple_logging import SimpleLogging
from translation import i18n

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()

__addon__ = xbmcaddon.Addon(id='plugin.video.embycon')


def showGenreList():
    log.debug("== ENTER: showGenreList() ==")

    server = downloadUtils.getServer()
    if server is None:
        return

    detailsString = getDetailsString()

    try:
        jsonData = downloadUtils.downloadUrl("{server}/emby/Genres?SortBy=SortName&SortOrder=Ascending&IncludeTypes=Movie&Recursive=true&UserId={userid}&format=json")
        log.debug("GENRE_LIST_DATA : " + jsonData)
    except Exception, msg:
        error = "Get connect : " + str(msg)
        log.error(error)

    result = json.loads(jsonData)
    result = result.get("Items")

    collections = []

    for genre in result:
        item_data = {}
        item_data['title'] = genre.get("Name")
        item_data['media_type'] = "Movies"
        item_data['thumbnail'] = downloadUtils.getArtwork(genre, "Thumb", server=server)
        item_data['path'] = ('{server}/emby/Users/{userid}/Items?Fields=' + detailsString +
                             '&Recursive=true&GenreIds=' + genre.get("Id") +
                             '&IncludeItemTypes=Movie' +
                             '&ImageTypeLimit=1&format=json')
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + ("?url=" + urllib.quote(collection['path']) +
                             "&mode=GET_CONTENT" +
                             "&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: " + collection.get('title', i18n('unknown')) + " " + str(url))
        addMenuDirectoryItem(collection.get('title', i18n('unknown')), url, thumbnail=collection.get("thumbnail"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def showMovieAlphaList():
    log.debug("== ENTER: showMovieAlphaList() ==")

    settings = xbmcaddon.Addon(id='plugin.video.embycon')
    server = downloadUtils.getServer()
    if server is None:
        return
    detailsString = getDetailsString()

    collections = []

    item_data = {}
    item_data['title'] = "#"
    item_data['media_type'] = "Movies"
    item_data['path'] = ('{server}/emby/Users/{userid}' +
                         '/Items?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&NameLessThan=A' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['title'] = alphaName
        item_data['media_type'] = "Movies"
        item_data['path'] = ('{server}/emby/Users/{userid}' +
                             '/Items?Fields=' + detailsString +
                             '&Recursive=true' +
                             '&NameStartsWith=' + alphaName +
                             '&IncludeItemTypes=Movie' +
                             '&ImageTypeLimit=1&format=json')
        collections.append(item_data)

    for collection in collections:
        url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
               "&mode=GET_CONTENT&media_type=" + collection["media_type"])
        log.debug("addMenuDirectoryItem: " + collection.get('title', i18n('unknown')) + " " + str(url))
        addMenuDirectoryItem(collection.get('title', i18n('unknown')), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def displaySections():
    log.debug("== ENTER: displaySections() ==")
    xbmcplugin.setContent(int(sys.argv[1]), 'files')

    server = downloadUtils.getServer()
    if server is None:
        return

    # Add collections
    detailsString = getDetailsString()
    collections = getCollections(detailsString)

    if collections:
        for collection in collections:
            url = (sys.argv[0] + "?url=" + urllib.quote(collection['path']) +
                   "&mode=GET_CONTENT&media_type=" + collection["media_type"])
            if collection.get("name_format") is not None:
                url += "&name_format=" + urllib.quote(collection.get("name_format"))
            log.debug("addMenuDirectoryItem: " + collection.get('title', i18n('unknown')) + " " + str(url))
            addMenuDirectoryItem(collection.get('title', i18n('unknown')), url, thumbnail=collection.get("thumbnail"))

        addMenuDirectoryItem(i18n('movies_genre'), "plugin://plugin.video.embycon/?mode=MOVIE_GENRA")
        addMenuDirectoryItem(i18n('movies_az'), "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA")
        addMenuDirectoryItem(i18n('search'), "plugin://plugin.video.embycon/?mode=SEARCH")

        addMenuDirectoryItem(i18n('show_clients'), "plugin://plugin.video.embycon/?mode=SHOW_SERVER_SESSIONS")
        addMenuDirectoryItem(i18n('change_user'), "plugin://plugin.video.embycon/?mode=CHANGE_USER")

    addMenuDirectoryItem(i18n('detect_server'), "plugin://plugin.video.embycon/?mode=DETECT_SERVER_USER")
    addMenuDirectoryItem(i18n('show_settings'), "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")

    if collections:
        addMenuDirectoryItem(i18n('widgets'), "plugin://plugin.video.embycon/?mode=WIDGETS")

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def getCollections(detailsString):
    log.debug("== ENTER: getCollections ==")

    server = downloadUtils.getServer()
    if server is None:
        return []

    userid = downloadUtils.getUserId()

    if userid == None or len(userid) == 0:
        log.debug("No userid so returning []")
        return []

    try:
        jsonData = downloadUtils.downloadUrl("{server}/emby/Users/{userid}/Items/Root?format=json")
    except Exception, msg:
        error = "Get connect : " + str(msg)
        log.error(error)
        return []

    log.debug("jsonData : " + jsonData)
    result = json.loads(jsonData)
    if result is None:
        return []

    parentid = result.get("Id")
    log.debug("parentid : " + parentid)

    htmlpath = "{server}/emby/Users/{userid}/items?ParentId=" + parentid + "&Sortby=SortName&format=json"
    jsonData = downloadUtils.downloadUrl(htmlpath)
    log.debug("jsonData : " + jsonData)
    collections = []

    result = []
    try:
        result = json.loads(jsonData)
        result = result.get("Items")
    except Exception as error:
        log.error("Error parsing user collection: " + str(error))

    for item in result:
        item_name = (item.get("Name")).encode('utf-8')

        collection_type = item.get('CollectionType', None)
        log.debug("CollectionType: " + str(collection_type))
        log.debug("Title: " + item_name)

        if collection_type in ["tvshows", "movies", "boxsets"]:
            collections.append({
                'title': item_name,
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

        if collection_type == "tvshows":
            collections.append({
                'title': item_name + i18n('_unwatched'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&Filters=IsUnplayed' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'tvshows'})
            collections.append({
                'title': item_name + i18n('_in_progress'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&Filters=IsResumable' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'episode_name_format'})
            collections.append({
                'title': item_name + i18n('_recently_added'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'episode_name_format'})
            collections.append({
                'title': item_name + i18n('_next_up'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields=' + detailsString +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': 'Episodes',
                'name_format': 'episode_name_format'})

        if collection_type == "movies":
            collections.append({
                'title': item_name + i18n('_unwatched'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&Filters=IsUnplayed' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})
            collections.append({
                'title': item_name + i18n('_in_progress'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&Filters=IsResumable' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})
            collections.append({
                'title': item_name + i18n('_recently_added'),
                'thumbnail': downloadUtils.getArtwork(item, "Primary", server=server),
                'path': ('{server}/emby/Users/{userid}/Items' +
                         '?ParentId=' + item.get("Id") +
                         '&Limit={ItemLimit}' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&Fields=' + detailsString +
                         '&SortBy=DateCreated' +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&ImageTypeLimit=1' +
                         '&format=json'),
                'media_type': collection_type})

    # Add standard nodes
    item_data = {}
    item_data['title'] = i18n('movies_all')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_unwatched')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&Fields=' + detailsString +
                         '&Filters=IsUnplayed' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_in_progress')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields=' + detailsString +
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
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields=' + detailsString +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_favorites')
    item_data['media_type'] = 'Movies'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&Filters=IsFavorite' +
                         '&IncludeItemTypes=Movie' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('movies_boxsets')
    item_data['media_type'] = 'BoxSets'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&Fields=' + detailsString +
                         '&IncludeItemTypes=BoxSet' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('tvshows_all')
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('tvshows_unwatched')
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&Filters=IsUnplayed' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('tvshows_favorites')
    item_data['media_type'] = 'tvshows'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Fields=' + detailsString +
                         '&Recursive=true' +
                         '&Filters=IsFavorite' +
                         '&IncludeItemTypes=Series' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('episodes_in_progress')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields=' + detailsString +
                         '&Filters=IsResumable' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('episodes_recently_added')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&SortBy=DateCreated' +
                         '&Fields=' + detailsString +
                         '&SortOrder=Descending' +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('episodes_up_next')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Shows/NextUp/?Userid={userid}' +
                         '&Limit={ItemLimit}' +
                         '&Recursive=true' +
                         '&Fields=' + detailsString +
                         '&Filters=IsUnplayed,IsNotFolder' +
                         '&IsVirtualUnaired=false' +
                         '&IsMissing=False' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    item_data['name_format'] = 'episode_name_format'
    collections.append(item_data)

    item_data = {}
    item_data['title'] = i18n('upcoming_tv')
    item_data['media_type'] = 'Episodes'
    item_data['path'] = ('{server}/emby/Users/{userid}/Items' +
                         '?Recursive=true' +
                         '&SortBy=PremiereDate' +
                         '&Fields=' + detailsString +
                         '&SortOrder=Ascending' +
                         '&IsVirtualUnaired=true' +
                         '&IsNotFolder' +
                         '&IncludeItemTypes=Episode' +
                         '&ImageTypeLimit=1' +
                         '&format=json')
    collections.append(item_data)

    return collections


def showWidgets():
    addMenuDirectoryItem(i18n('emby_movies'), 'plugin://plugin.video.embycon/?mode=SHOW_CONTENT&item_type=Movie&media_type=Movies')
    addMenuDirectoryItem(i18n('emby_tvshows'), 'plugin://plugin.video.embycon/?mode=SHOW_CONTENT&item_type=Series&media_type=TVShows')

    addMenuDirectoryItem(i18n('movies_recently_added'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_movies')
    addMenuDirectoryItem(i18n('movies_in_progress'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_movies')
    addMenuDirectoryItem(i18n('movies_random'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=random_movies')
    addMenuDirectoryItem(i18n('episodes_recently_added'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=recent_episodes')
    addMenuDirectoryItem(i18n('episodes_in_progress'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=inprogress_episodes')
    addMenuDirectoryItem(i18n('episodes_up_next'), 'plugin://plugin.video.embycon/?mode=WIDGET_CONTENT&type=nextup_episodes')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def showSearch():
    addMenuDirectoryItem(i18n('movies'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Movie')
    addMenuDirectoryItem(i18n('tvshows'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Series')
    addMenuDirectoryItem(i18n('episodes'), 'plugin://plugin.video.embycon/?mode=NEW_SEARCH&item_type=Episode')

    xbmcplugin.endOfDirectory(int(sys.argv[1]))
