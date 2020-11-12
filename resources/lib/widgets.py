from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import json
import hashlib
import random
import time

from .downloadutils import DownloadUtils
from .utils import get_jellyfin_url
from .datamanager import DataManager
from .loghandler import LazyLogger
from .kodi_utils import HomeWindow
from .dir_functions import process_directory
from .tracking import timer

log = LazyLogger(__name__)
downloadUtils = DownloadUtils()
dataManager = DataManager()
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

background_items = []
background_current_item = 0


@timer
def set_random_movies():
    log.debug("set_random_movies Called")

    settings = xbmcaddon.Addon()
    hide_watched = settings.getSetting("hide_watched") == "true"

    url_params = {}
    url_params["Recursive"] = True
    url_params["limit"] = 20
    if hide_watched:
        url_params["IsPlayed"] = False
    url_params["SortBy"] = "Random"
    url_params["IncludeItemTypes"] = "Movie"
    url_params["ImageTypeLimit"] = 0

    url = get_jellyfin_url("{server}/Users/{userid}/Items", url_params)

    results = downloadUtils.download_url(url, suppress=True)

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

    log.debug("set_random_movies : {0}".format(movies_list_string))
    log.debug("set_random_movies : {0}".format(new_widget_hash))
    home_window.set_property("random-movies", movies_list_string)
    home_window.set_property("random-movies-changed", new_widget_hash)


def set_background_image(force=False):
    log.debug("set_background_image Called forced={0}".format(force))

    global background_current_item
    global background_items

    if force:
        background_current_item = 0
        del background_items
        background_items = []

    if len(background_items) == 0:
        log.debug("set_background_image: Need to load more backgrounds {0} - {1}".format(
             len(background_items), background_current_item))

        url_params = {}
        url_params["Recursive"] = True
        url_params["limit"] = 100
        url_params["SortBy"] = "Random"
        url_params["IncludeItemTypes"] = "Movie,Series"
        url_params["ImageTypeLimit"] = 1

        url = get_jellyfin_url('{server}/Users/{userid}/Items', url_params)

        server = downloadUtils.get_server()
        results = downloadUtils.download_url(url, suppress=True)

        if results is not None:
            items = results.get("Items", [])
            background_current_item = 0
            background_items = []
            for item in items:
                bg_image = downloadUtils.get_artwork(item, "Backdrop", server=server)
                if bg_image:
                    label = item.get("Name")
                    item_background = {}
                    item_background["image"] = bg_image
                    item_background["name"] = label
                    background_items.append(item_background)

        log.debug("set_background_image: Loaded {0} more backgrounds".format(len(background_items)))

    if len(background_items) > 0:
        bg_image = background_items[background_current_item].get("image")
        label = background_items[background_current_item].get("name")
        log.debug("set_background_image: {0} - {1} - {2}".format(background_current_item, label, bg_image))

        background_current_item += 1
        if background_current_item >= len(background_items):
            background_current_item = 0

        home_window = HomeWindow()
        home_window.set_property("random-gb", bg_image)
        home_window.set_property("random-gb-label", label)


@timer
def check_for_new_content():
    log.debug("checkForNewContent Called")

    home_window = HomeWindow()
    settings = xbmcaddon.Addon()
    simple_new_content_check = settings.getSetting("simple_new_content_check") == "true"

    if simple_new_content_check:
        log.debug("Using simple new content check")
        current_time_stamp = str(time.time())
        home_window.set_property("jellycon_widget_reload", current_time_stamp)
        log.debug("Setting New Widget Hash: {0}".format(current_time_stamp))
        return

    url_params = {}
    url_params["Recursive"] = True
    url_params["limit"] = 1
    url_params["Fields"] = "DateCreated,Etag"
    url_params["SortBy"] = "DateCreated"
    url_params["SortOrder"] = "Descending"
    url_params["IncludeItemTypes"] = "Movie,Episode"
    url_params["ImageTypeLimit"] = 0
    url_params["format"] = "json"

    added_url = get_jellyfin_url('{server}/Users/{userid}/Items', url_params)

    result = downloadUtils.download_url(added_url, suppress=True)
    log.debug("LATEST_ADDED_ITEM: {0}".format(result))

    last_added_date = ""
    if result is not None:
        items = result.get("Items", [])
        if len(items) > 0:
            item = items[0]
            last_added_date = item.get("Etag", "")
    log.debug("last_added_date: {0}".format(last_added_date))

    url_params = {}
    url_params["Recursive"] = True
    url_params["limit"] = 1
    url_params["Fields"] = "DateCreated,Etag"
    url_params["SortBy"] = "DatePlayed"
    url_params["SortOrder"] = "Descending"
    url_params["IncludeItemTypes"] = "Movie,Episode"
    url_params["ImageTypeLimit"] = 0
    url_params["format"] = "json"

    played_url = get_jellyfin_url('{server}/Users/{userid}/Items', url_params)

    result = downloadUtils.download_url(played_url, suppress=True)
    log.debug("LATEST_PLAYED_ITEM: {0}".format(result))

    last_played_date = ""
    if result is not None:
        items = result.get("Items", [])
        if len(items) > 0:
            item = items[0]
            # last_played_date = item.get("Etag", "")
            user_data = item.get("UserData", None)
            if user_data is not None:
                last_played_date = user_data.get("LastPlayedDate", "")

    log.debug("last_played_date: {0}".format(last_played_date))

    current_widget_hash = home_window.get_property("jellycon_widget_reload")
    log.debug("Current Widget Hash: {0}".format(current_widget_hash))

    m = hashlib.md5()
    m.update(last_played_date + last_added_date)
    new_widget_hash = m.hexdigest()
    log.debug("New Widget Hash: {0}".format(new_widget_hash))

    if current_widget_hash != new_widget_hash:
        home_window.set_property("jellycon_widget_reload", new_widget_hash)
        log.debug("Setting New Widget Hash: {0}".format(new_widget_hash))


@timer
def get_widget_content_cast(handle, params):
    log.debug("getWigetContentCast Called: {0}".format(params))
    server = downloadUtils.get_server()

    item_id = params["id"]
    data_manager = DataManager()
    result = data_manager.get_content("{server}/Users/{userid}/Items/" + item_id + "?format=json")
    log.debug("ItemInfo: {0}".format(result))

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
                person_thumbnail = downloadUtils.image_url(person_id, "Primary", 0, 400, 400, person_tag, server=server)

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


@timer
def get_widget_content(handle, params):
    log.debug("getWigetContent Called: {0}".format(params))

    settings = xbmcaddon.Addon()
    hide_watched = settings.getSetting("hide_watched") == "true"
    use_cached_widget_data = settings.getSetting("use_cached_widget_data") == "true"

    widget_type = params.get("type")
    if widget_type is None:
        log.error("getWigetContent type not set")
        return

    log.debug("widget_type: {0}".format(widget_type))

    url_verb = "{server}/Users/{userid}/Items"
    url_params = {}
    url_params["Limit"] = "{ItemLimit}"
    url_params["format"] = "json"
    url_params["Fields"] = "{field_filters}"
    url_params["ImageTypeLimit"] = 1
    url_params["IsMissing"] = False

    if widget_type == "recent_movies":
        xbmcplugin.setContent(handle, 'movies')
        url_params["Recursive"] = True
        url_params["SortBy"] = "DateCreated"
        url_params["SortOrder"] = "Descending"
        url_params["Filters"] = "IsNotFolder"
        if hide_watched:
            url_params["IsPlayed"] = False
        url_params["IsVirtualUnaired"] = False
        url_params["IncludeItemTypes"] = "Movie"

    elif widget_type == "inprogress_movies":
        xbmcplugin.setContent(handle, 'movies')
        url_params["Recursive"] = True
        url_params["SortBy"] = "DatePlayed"
        url_params["SortOrder"] = "Descending"
        url_params["Filters"] = "IsResumable"
        url_params["IsVirtualUnaired"] = False
        url_params["IncludeItemTypes"] = "Movie"

    elif widget_type == "random_movies":
        xbmcplugin.setContent(handle, 'movies')
        url_params["Ids"] = "{random_movies}"

    elif widget_type == "recent_tvshows":
        xbmcplugin.setContent(handle, 'episodes')
        url_verb = '{server}/Users/{userid}/Items/Latest'
        url_params["GroupItems"] = True
        url_params["Limit"] = 45
        url_params["Recursive"] = True
        url_params["SortBy"] = "DateCreated"
        url_params["SortOrder"] = "Descending"
        url_params["Fields"] = "{field_filters}"
        if hide_watched:
            url_params["IsPlayed"] = False
        url_params["IsVirtualUnaired"] = False
        url_params["IncludeItemTypes"] = "Episode"
        url_params["ImageTypeLimit"] = 1
        url_params["format"] = "json"

    elif widget_type == "recent_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        url_params["Recursive"] = True
        url_params["SortBy"] = "DateCreated"
        url_params["SortOrder"] = "Descending"
        url_params["Filters"] = "IsNotFolder"
        if hide_watched:
            url_params["IsPlayed"] = False
        url_params["IsVirtualUnaired"] = False
        url_params["IncludeItemTypes"] = "Episode"

    elif widget_type == "inprogress_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        url_params["Recursive"] = True
        url_params["SortBy"] = "DatePlayed"
        url_params["SortOrder"] = "Descending"
        url_params["Filters"] = "IsResumable"
        url_params["IsVirtualUnaired"] = False
        url_params["IncludeItemTypes"] = "Episode"

    elif widget_type == "nextup_episodes":
        xbmcplugin.setContent(handle, 'episodes')
        url_verb = "{server}/Shows/NextUp"
        url_params["Limit"] = "{ItemLimit}"
        url_params["userid"] = "{userid}"
        url_params["Recursive"] = True
        url_params["Fields"] = "{field_filters}"
        url_params["format"] = "json"
        url_params["ImageTypeLimit"] = 1

    elif widget_type == "movie_recommendations":
        suggested_items_url_params = {}
        suggested_items_url_params["userId"] = "{userid}"
        suggested_items_url_params["categoryLimit"] = 15
        suggested_items_url_params["ItemLimit"] = 20
        suggested_items_url_params["ImageTypeLimit"] = 0
        suggested_items_url = get_jellyfin_url("{server}/Movies/Recommendations", suggested_items_url_params)

        data_manager = DataManager()
        suggested_items = data_manager.get_content(suggested_items_url)
        ids = []
        set_id = 0
        while len(ids) < 20 and suggested_items:
            items = suggested_items[set_id]
            log.debug("BaselineItemName : {0} - {1}".format(set_id, items.get("BaselineItemName")))
            items = items["Items"]
            rand = random.randint(0, len(items) - 1)
            # log.debug("random suggestions index : {0} {1}", rand, set_id)
            item = items[rand]
            if item["Type"] == "Movie" and item["Id"] not in ids and (not item["UserData"]["Played"] or not hide_watched):
                # log.debug("random suggestions adding : {0}", item["Id"])
                ids.append(item["Id"])
            # else:
            #     log.debug("random suggestions not valid : {0} - {1} - {2}", item["Id"], item["Type"], item["UserData"]["Played"])
            del items[rand]
            # log.debug("items len {0}", len(items))
            if len(items) == 0:
                # log.debug("Removing Set {0}", set_id)
                del suggested_items[set_id]
            set_id += 1
            if set_id >= len(suggested_items):
                set_id = 0

        id_list = ",".join(ids)
        log.debug("Recommended Items : {0}".format(len(ids), id_list))
        url_params["Ids"] = id_list

    items_url = get_jellyfin_url(url_verb, url_params)

    list_items, detected_type, total_records = process_directory(items_url, None, params, use_cached_widget_data)

    # remove resumable items from next up
    if widget_type == "nextup_episodes":
        filtered_list = []
        for item in list_items:
            resume_time = item[1].getProperty("ResumeTime")
            if resume_time is None or float(resume_time) == 0.0:
                filtered_list.append(item)
        list_items = filtered_list

    # list_items = populateWidgetItems(items_url, widget_type)

    if detected_type is not None:
        # if the media type is not set then try to use the detected type
        log.debug("Detected content type: {0}".format(detected_type))
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

    xbmcplugin.addDirectoryItems(handle, list_items)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
