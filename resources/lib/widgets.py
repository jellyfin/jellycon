import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import json
import urllib
import hashlib
import time
import random
import sys

from .downloadutils import DownloadUtils
from .utils import getArt
from .datamanager import DataManager
from .simple_logging import SimpleLogging
from .kodi_utils import HomeWindow
from .dir_functions import processDirectory

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()
dataManager = DataManager()
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

background_items = []
background_current_item = 0


def set_random_movies():
    log.debug("set_random_movies Called")

    url = ('{server}/emby/Users/{userid}/Items' +
           '?Recursive=true' +
           '&limit=20' +
           '&Filters=IsUnplayed' +
           '&IsPlayed=false' +
           '&SortBy=Random' +
           '&IncludeItemTypes=Movie' +
           '&ImageTypeLimit=0')
    results = downloadUtils.downloadUrl(url, suppress=True)
    results = json.loads(results)

    randon_movies_list = []
    if results is not None:
        items = results.get("Items", [])
        for item in items:
            randon_movies_list.append(item.get("Id"))

    random.shuffle(randon_movies_list)
    movies_list_string = ",".join(randon_movies_list)
    home_window = HomeWindow()
    m = hashlib.md5()
    m.update(movies_list_string)
    new_widget_hash = m.hexdigest()

    log.debug("set_random_movies : {0}", movies_list_string)
    log.debug("set_random_movies : {0}", new_widget_hash)
    home_window.setProperty("random-movies", movies_list_string)
    home_window.setProperty("random-movies-changed", new_widget_hash)


def set_background_image(force=False):
    log.debug("set_background_image Called forced={0}", force)

    global background_current_item
    global background_items

    if force:
        background_current_item = 0
        del background_items
        background_items = []

    if len(background_items) == 0:
        log.debug("set_background_image: Need to load more backgrounds {0} - {1}",
                  len(background_items), background_current_item)
        url = ('{server}/emby/Users/{userid}/Items' +
               '?Recursive=true' +
               # '&limit=60' +
               '&SortBy=Random' +
               '&IncludeItemTypes=Movie,Series' +
               '&ImageTypeLimit=1')

        server = downloadUtils.getServer()
        results = downloadUtils.downloadUrl(url, suppress=True)
        results = json.loads(results)

        if results is not None:
            items = results.get("Items", [])
            background_current_item = 0
            background_items = []
            for item in items:
                bg_image = downloadUtils.getArtwork(item, "Backdrop", server=server)
                if bg_image:
                    label = item.get("Name")
                    item_background = {}
                    item_background["image"] = bg_image
                    item_background["name"] = label
                    background_items.append(item_background)

        log.debug("set_background_image: Loaded {0} more backgrounds", len(background_items))

    if len(background_items) > 0:
        bg_image = background_items[background_current_item].get("image")
        label = background_items[background_current_item].get("name")
        log.debug("set_background_image: {0} - {1} - {2}", background_current_item, label, bg_image)

        background_current_item += 1
        if background_current_item >= len(background_items):
            background_current_item = 0

        home_window = HomeWindow()
        home_window.setProperty("random-gb", bg_image)
        home_window.setProperty("random-gb-label", label)


def checkForNewContent():
    log.debug("checkForNewContent Called")

    added_url = ('{server}/emby/Users/{userid}/Items' +
                 '?Recursive=true' +
                 '&limit=1' +
                 '&Fields=DateCreated,Etag' +
                 '&SortBy=DateCreated' +
                 '&SortOrder=Descending' +
                 '&IncludeItemTypes=Movie,Episode' +
                 '&ImageTypeLimit=0' +
                 '&format=json')

    added_result = downloadUtils.downloadUrl(added_url, suppress=True)
    result = json.loads(added_result)
    log.debug("LATEST_ADDED_ITEM: {0}", result)

    last_added_date = ""
    if result is not None:
        items = result.get("Items", [])
        if len(items) > 0:
            item = items[0]
            last_added_date = item.get("Etag", "")
    log.debug("last_added_date: {0}", last_added_date)

    played_url = ('{server}/emby/Users/{userid}/Items' +
                  '?Recursive=true' +
                  '&limit=1' +
                  '&Fields=DateCreated,Etag' +
                  '&SortBy=DatePlayed' +
                  '&SortOrder=Descending' +
                  '&IncludeItemTypes=Movie,Episode' +
                  '&ImageTypeLimit=0' +
                  '&format=json')

    played_result = downloadUtils.downloadUrl(played_url, suppress=True)
    result = json.loads(played_result)
    log.debug("LATEST_PLAYED_ITEM: {0}", result)

    last_played_date = ""
    if result is not None:
        items = result.get("Items", [])
        if len(items) > 0:
            item = items[0]
            last_played_date = item.get("Etag", "")
    log.debug("last_played_date: {0}", last_played_date)

    home_window = HomeWindow()
    current_widget_hash = home_window.getProperty("embycon_widget_reload")
    log.debug("Current Widget Hash: {0}", current_widget_hash)

    m = hashlib.md5()
    m.update(last_played_date + last_added_date)
    new_widget_hash = m.hexdigest()
    log.debug("New Widget Hash: {0}", new_widget_hash)

    if current_widget_hash != new_widget_hash:
        home_window.setProperty("embycon_widget_reload", new_widget_hash)
        log.debug("Setting New Widget Hash: {0}", new_widget_hash)
        return True
    else:
        return False


def get_widget_content_cast(handle, params):
    log.debug("getWigetContentCast Called: {0}", params)
    server = downloadUtils.getServer()

    item_id = params["id"]
    data_manager = DataManager()
    result = data_manager.GetContent("{server}/emby/Users/{userid}/Items/" + item_id + "?format=json")
    log.debug("ItemInfo: {0}", result)

    if not result:
        return

    if result.get("Type", "") in ["Episode", "Season"] and params.get("auto", "true") == "true":
        series_id = result.get("SeriesId")
        if series_id:
            params["id"] = series_id
            return get_widget_content_cast(handle, params)

    list_items = []
    if result is not None:
        people = result.get("People", [])
    else:
        people = []

    for person in people:
        # if (person.get("Type") == "Director"):
        #     director = director + person.get("Name") + ' '
        # if (person.get("Type") == "Writing"):
        #     writer = person.get("Name")
        # if (person.get("Type") == "Writer"):
        #    writer = person.get("Name")
        if person.get("Type") == "Actor":
            person_name = person.get("Name")
            person_role = person.get("Role")
            person_id = person.get("Id")
            person_tag = person.get("PrimaryImageTag")
            person_thumbnail = None
            if person_tag:
                person_thumbnail = downloadUtils.imageUrl(person_id, "Primary", 0, 400, 400, person_tag, server=server)

            if kodi_version > 17:
                list_item = xbmcgui.ListItem(label=person_name, offscreen=True)
            else:
                list_item = xbmcgui.ListItem(label=person_name)

            list_item.setProperty("id", person_id)

            if person_thumbnail:
                art_links = {}
                art_links["thumb"] = person_thumbnail
                art_links["poster"] = person_thumbnail
                list_item.setArt(art_links)

            labels = {}
            labels["mediatype"] = "artist"
            list_item.setInfo(type="music", infoLabels=labels)

            if person_role:
                list_item.setLabel2(person_role)

            item_tupple = ("", list_item, False)
            list_items.append(item_tupple)

    xbmcplugin.setContent(handle, 'artists')
    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def getWidgetContent(handle, params):
    log.debug("getWigetContent Called: {0}", params)

    widget_type = params.get("type")
    if widget_type is None:
        log.error("getWigetContent type not set")
        return

    log.debug("widget_type: {0}", widget_type)

    items_url = ("{server}/emby/Users/{userid}/Items" +
                 "?Limit={ItemLimit}" +
                 "&format=json" +
                 '&Fields={field_filters}' +
                 "&ImageTypeLimit=1" +
                 "&IsMissing=False")

    if widget_type == "recent_movies":
        xbmcplugin.setContent(handle, 'movies')
        items_url += ("&Recursive=true" +
                      "&SortBy=DateCreated" +
                      "&SortOrder=Descending" +
                      "&Filters=IsUnplayed,IsNotFolder" +
                      "&IsPlayed=false" +
                      "&IsVirtualUnaired=false" +
                      "&IsMissing=False" +
                      "&IncludeItemTypes=Movie")

    elif widget_type == "inprogress_movies":
        xbmcplugin.setContent(handle, 'movies')
        items_url += ("&Recursive=true" +
                      "&SortBy=DatePlayed" +
                      "&SortOrder=Descending" +
                      "&Filters=IsResumable" +
                      "&IsVirtualUnaired=false" +
                      "&IsMissing=False" +
                      "&IncludeItemTypes=Movie")

    elif widget_type == "random_movies":
        xbmcplugin.setContent(handle, 'movies')
        items_url += "&Ids={random_movies}"

    elif widget_type == "recent_tvshows":
        xbmcplugin.setContent(handle, 'episodes')
        items_url = ('{server}/emby/Users/{userid}/Items/Latest' +
                     '?GroupItems=true' +
                     '&Limit=45' +
                     '&Recursive=true' +
                     '&SortBy=DateCreated' +
                     '&SortOrder=Descending' +
                     '&Filters=IsUnplayed' +
                     '&Fields={field_filters}' +
                     '&IsPlayed=false' +
                     '&IsVirtualUnaired=false' +
                     '&IsMissing=False' +
                     '&IncludeItemTypes=Episode' +
                     '&ImageTypeLimit=1' +
                     '&format=json')

    elif widget_type == "recent_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        items_url += ("&Recursive=true" +
                      "&SortBy=DateCreated" +
                      "&SortOrder=Descending" +
                      "&Filters=IsUnplayed,IsNotFolder" +
                      "&IsPlayed=false" +
                      "&IsVirtualUnaired=false" +
                      "&IsMissing=False" +
                      "&IncludeItemTypes=Episode")

    elif widget_type == "inprogress_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        items_url += ("&Recursive=true" +
                      "&SortBy=DatePlayed" +
                      "&SortOrder=Descending" +
                      "&Filters=IsResumable" +
                      "&IsVirtualUnaired=false" +
                      "&IsMissing=False" +
                      "&IncludeItemTypes=Episode")

    elif widget_type == "nextup_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        items_url = ("{server}/emby/Shows/NextUp" +
                     "?Limit={ItemLimit}"
                     "&userid={userid}" +
                     "&Recursive=true" +
                     '&Fields={field_filters}' +
                     "&format=json" +
                     "&ImageTypeLimit=1")

    list_items, detected_type, total_records = processDirectory(items_url, None, params, False)

    # remove resumable items from next up
    if widget_type == "nextup_episodes":
        filtered_list = []
        for item in list_items:
            resume_time = item[1].getProperty("ResumeTime")
            if resume_time is None or float(resume_time) == 0.0:
                filtered_list.append(item)
        list_items = filtered_list

    #list_items = populateWidgetItems(items_url, widget_type)

    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
