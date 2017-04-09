# Gnu General Public License - see LICENSE.TXT

import sys
import json as json
import urllib

import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc

from downloadutils import DownloadUtils
from utils import getDetailsString
from simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon." + __name__)
downloadUtils = DownloadUtils()

__settings__ = xbmcaddon.Addon(id='plugin.video.embycon')

def showGenreList():
    log.info("== ENTER: showGenreList() ==")

    server = __settings__.getSetting('ipaddress') + ":" + __settings__.getSetting('port')
    userid = downloadUtils.getUserId()
    detailsString = getDetailsString()

    try:
        jsonData = downloadUtils.downloadUrl(server + "/emby/Genres?SortBy=SortName&SortOrder=Ascending&IncludeTypes=Movie&Recursive=true&UserId=" + userid + "&format=json")
        log.info("GENRE_LIST_DATA : " + jsonData)
    except Exception, msg:
        error = "Get connect : " + str(msg)
        log.error(error)

    result = json.loads(jsonData)
    result = result.get("Items")

    collections = []

    for genre in result:
        item_data = {}
        item_data['address'] = server
        item_data['title'] = genre.get("Name")
        item_data['thumbnail'] = downloadUtils.getArtwork(genre, "Thumb")
        item_data['path'] = '/emby/Users/' + userid + '/Items?Fields=' + detailsString + '&Recursive=true&GenreIds=' + genre.get("Id") + '&IncludeItemTypes=Movie&CollapseBoxSetItems=true&ImageTypeLimit=1&format=json'
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + "?url=" + urllib.quote('http://%s%s' % (collection['address'], collection['path'])) + "&mode=GET_CONTENT"
        log.info("addMenuDirectoryItem: " + collection.get('title', 'Unknown') + " " + str(url))
        addMenuDirectoryItem(collection.get('title', 'Unknown'), url, thumbnail=collection.get("thumbnail"))

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def showMovieAlphaList():
    log.info("== ENTER: showMovieAlphaList() ==")

    server = __settings__.getSetting('ipaddress') + ":" + __settings__.getSetting('port')
    userid = downloadUtils.getUserId()
    detailsString = getDetailsString()

    collections = []

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "#"
    item_data['path'] = '/emby/Users/' + userid + '/Items?Fields=' + detailsString + '&Recursive=true&NameLessThan=A&IncludeItemTypes=Movie&CollapseBoxSetItems=true&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    alphaList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]

    for alphaName in alphaList:
        item_data = {}
        item_data['address'] = server
        item_data['title'] = alphaName
        item_data['path'] = '/emby/Users/' + userid + '/Items?Fields=' + detailsString + '&Recursive=true&NameStartsWith=' + alphaName + '&IncludeItemTypes=Movie&CollapseBoxSetItems=true&ImageTypeLimit=1&format=json'
        collections.append(item_data)

    for collection in collections:
        url = sys.argv[0] + "?url=" + urllib.quote('http://%s%s' % (collection['address'], collection['path'])) + "&mode=GET_CONTENT"
        log.info("addMenuDirectoryItem: " + collection.get('title', 'Unknown') + " " + str(url))
        addMenuDirectoryItem(collection.get('title', 'Unknown'), url)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def displaySections():
    log.info("== ENTER: displaySections() ==")
    xbmcplugin.setContent(int(sys.argv[1]), 'files')

    # Add collections
    detailsString = getDetailsString()
    collections = getCollections(detailsString)
    for collection in collections:
        url = sys.argv[0] + "?url=" + urllib.quote('http://%s%s' % (collection['address'], collection['path'])) + "&mode=GET_CONTENT"
        log.info("addMenuDirectoryItem: " + collection.get('title', 'Unknown') + " " + str(url))
        addMenuDirectoryItem(collection.get('title', 'Unknown'), url, thumbnail=collection.get("thumbnail"))

    addMenuDirectoryItem("Movies (Genre)", "plugin://plugin.video.embycon/?mode=MOVIE_GENRA")
    addMenuDirectoryItem("Movies (A-Z)", "plugin://plugin.video.embycon/?mode=MOVIE_ALPHA")
    addMenuDirectoryItem("Change User", "plugin://plugin.video.embycon/?mode=CHANGE_USER")
    addMenuDirectoryItem("Show Settings", "plugin://plugin.video.embycon/?mode=SHOW_SETTINGS")
    addMenuDirectoryItem("Set Default Views", "plugin://plugin.video.embycon/?mode=SET_DEFAULT_VIEWS")

    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def addMenuDirectoryItem(label, path, folder=True, thumbnail=None):
    li = xbmcgui.ListItem(label, path=path, thumbnailImage=thumbnail)
    if thumbnail:
        li.setThumbnailImage(thumbnail)
    else:
        li.setThumbnailImage("special://home/addons/plugin.video.embycon/icon.png")
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder)

def getCollections(detailsString):
    log.info("== ENTER: getCollections ==")

    server = __settings__.getSetting('ipaddress') + ":" + __settings__.getSetting('port')

    userid = downloadUtils.getUserId()
    if(userid == None or len(userid) == 0):
        return []

    try:
        jsonData = downloadUtils.downloadUrl(server + "/emby/Users/" + userid + "/Items/Root?format=json")
    except Exception, msg:
        error = "Get connect : " + str(msg)
        log.error(error)
        return []

    log.debug("jsonData : " + jsonData)
    result = json.loads(jsonData)

    parentid = result.get("Id")
    log.info("parentid : " + parentid)

    htmlpath = ("http://%s/emby/Users/" % server)
    jsonData = downloadUtils.downloadUrl(
        htmlpath + userid + "/items?ParentId=" + parentid + "&Sortby=SortName&format=json")
    log.debug("jsonData : " + jsonData)
    collections=[]

    result = []
    try:
        result = json.loads(jsonData)
        result = result.get("Items")
    except Exception as error:
        log.error("Error parsing user collection: " + str(error))

    for item in result:
        item_name = (item.get("Name")).encode('utf-8')

        collections.append({
            'title': item_name,
            'address': server,
            'thumbnail': downloadUtils.getArtwork(item, "Primary"),
            'path': ('/emby/Users/' + userid +
                     '/items?ParentId=' + item.get("Id") +
                     '&IsVirtualUnaired=false&IsMissing=False&Fields=' + detailsString +
                     '&CollapseBoxSetItems=true&ImageTypeLimit=1&format=json')})

        log.info("Title: " + item_name)

    # Add standard nodes
    item_data = {}
    item_data['address'] = server
    item_data['title'] = "All Movies"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Fields=' + detailsString + '&Recursive=true&IncludeItemTypes=Movie&CollapseBoxSetItems=true&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "BoxSets"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Recursive=true&Fields=' + detailsString + '&IncludeItemTypes=BoxSet&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "All TV"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Fields=' + detailsString + '&Recursive=true&IncludeItemTypes=Series&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "Recently Added Movies"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Limit=' + '20' + '&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "Recently Added Episodes"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Limit=' + '20' + '&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "In Progress Movies"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Limit=' + '20' + '&Recursive=true&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Movie&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "In Progress Episodes"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Limit=' + '20' + '&Recursive=true&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Episode&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "Next Episodes"
    item_data[
        'path'] = '/emby/Shows/NextUp/?Userid=' + userid + '&Limit=' + '20' + '&Recursive=true&Fields=' + detailsString + '&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    item_data = {}
    item_data['address'] = server
    item_data['title'] = "Upcoming TV"
    item_data[
        'path'] = '/emby/Users/' + userid + '/Items?Recursive=true&SortBy=PremiereDate&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsUnplayed&IsVirtualUnaired=true&IsNotFolder&IncludeItemTypes=Episode&ImageTypeLimit=1&format=json'
    collections.append(item_data)

    return collections