
import sys
import os
import urllib
import json

import xbmc
import xbmcaddon
import xbmcgui

from utils import getArt
from simple_logging import SimpleLogging
from translation import i18n
from downloadutils import DownloadUtils
from datamanager import DataManager

log = SimpleLogging(__name__)
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

addon_instance = xbmcaddon.Addon(id='plugin.video.embycon')
addon_path = addon_instance.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath(os.path.join(addon_path))

download_utils = DownloadUtils()

class ItemDetails():

    name = None
    id = None
    path = None
    is_folder = False
    plot = None
    series_name = None
    episode_number = 0
    season_number = 0
    track_number = 0

    art = None

    mpaa = None
    rating = None
    critic_rating = 0
    year = None
    premiere_date = ""
    date_added = ""
    location_type = None
    studio = None
    genre = ""
    play_count = 0
    director = ""
    writer = ""
    channels = ""
    video_codec = ""
    aspect_ratio = 0.0
    audio_codec = ""
    height = 0
    width = 0
    cast = None

    resume_time = 0
    duration = 0
    recursive_item_count = 0
    recursive_unplayed_items_count = 0
    total_seasons = 0
    total_episodes = 0
    watched_episodes = 0
    unwatched_episodes = 0
    number_episodes = 0
    original_title = None
    item_type = None
    subtitle_lang = ""
    subtitle_available = False

    favorite = "false"
    overlay = "0"

    name_format = ""
    mode = ""

def extract_item_info(item, gui_options):

    item_details = ItemDetails()

    item_details.id = item["Id"]
    item_details.is_folder = item["IsFolder"]
    item_details.item_type = item["Type"]
    item_details.location_type = item["LocationType"]

    if item_details.item_type == "Episode":
        item_details.episode_number = item["IndexNumber"]

    if item_details.item_type == "Episode":
        item_details.season_number = item["ParentIndexNumber"]
    elif item_details.item_type == "Season":
        item_details.season_number = item["IndexNumber"]

    if item_details.season_number is None:
        item_details.season_number = 0
    if item_details.episode_number is None:
        item_details.episode_number = 0

    if item_details.item_type == "Audio":
        item_details.track_number = item["IndexNumber"]

    # set the item name
    # override with name format string from request
    name_format = gui_options["name_format"]
    name_format_type = gui_options["name_format_type"]
    add_season_number = gui_options["add_season_number"]
    add_episode_number = gui_options["add_episode_number"]

    item_details.name = item["Name"]
    item_details.original_title = item_details.name

    if name_format is not None and item_details.item_type == name_format_type:
        nameInfo = {}
        nameInfo["ItemName"] = item["Name"]
        season_name = item["SeriesName"]
        if season_name:
            nameInfo["SeriesName"] = season_name
        else:
            nameInfo["SeriesName"] = ""
        nameInfo["SeasonIndex"] = u"%02d" % item_details.season_number
        nameInfo["EpisodeIndex"] = u"%02d" % item_details.episode_number
        log.debug("FormatName: {0} | {1}", name_format, nameInfo)
        item_details.name = unicode(name_format).format(**nameInfo).strip()

    else:
        if item_details.item_type == "Episode":
            prefix = ''
            if add_season_number:
                prefix = "S%02d" % item_details.season_number
                if add_episode_number:
                    prefix = prefix + "E"
            if add_episode_number:
                prefix = prefix + "%02d" % item_details.episode_number
            if prefix != '':
                item_details.name = prefix + ' - ' + item["Name"]

    year = item["ProductionYear"]
    prem_date = item["PremiereDate"]

    if year is not None:
        item_details.year = year
    elif item_details.year is None and prem_date is not None:
        item_details.year = int(prem_date[:4])

    if prem_date is not None:
        tokens = prem_date.split("T")
        item_details.premiere_date = tokens[0]

    create_date = item["DateCreated"]
    if create_date is not None:
        item_details.date_added = create_date.split('.')[0].replace('T', " ")

    # add the premiered date for Upcoming TV
    if item_details.location_type == "Virtual":
        airtime = item["AirTime"]
        item_details.name = item_details.name + ' - ' + item_details.premiere_date + ' - ' + str(airtime)

    # Process MediaStreams
    mediaStreams = item["MediaStreams"]
    if mediaStreams is not None:
        for mediaStream in mediaStreams:
            stream_type = mediaStream["Type"]
            if stream_type == "Video":
                item_details.video_codec = mediaStream["Codec"]
                item_details.height = mediaStream["Height"]
                item_details.width = mediaStream["Width"]
                aspect = mediaStream["AspectRatio"]
                if aspect is not None and len(aspect) >= 3:
                    try:
                        aspect_width, aspect_height = aspect.split(':')
                        item_details.aspect_ratio = float(aspect_width) / float(aspect_height)
                    except:
                        item_details.aspect_ratio = 1.85
            if stream_type == "Audio":
                item_details.audio_codec = mediaStream["Codec"]
                item_details.channels = mediaStream["Channels"]
            if stream_type == "Subtitle":
                item_details.subtitle_available = True
                sub_lang = mediaStream["Language"]
                if sub_lang is not None:
                    item_details.subtitle_lang = sub_lang

    # Process People
    people = item["People"]
    if people is not None:
        cast = []
        for person in people:
            person_type = person["Type"]
            if person_type == "Director":
                item_details.director = item_details.director + person["Name"] + ' '
            elif person_type == "Writing":
                item_details.writer = person["Name"]
            elif person_type == "Actor":
                log.debug("Person: {0}", person)
                person_name = person["Name"]
                person_role = person["Role"]
                person_id = person["Id"]
                person_tag = person["PrimaryImageTag"]
                if person_tag is not None:
                    person_thumbnail = download_utils.imageUrl(person_id, "Primary", 0, 400, 400, person_tag, server = gui_options["server"])
                else:
                    person_thumbnail = ""
                person = {"name": person_name, "role": person_role, "thumbnail": person_thumbnail}
                cast.append(person)
        item_details.cast = cast

    # Process Studios
    studios = item["Studios"]
    if studios is not None:
        for studio in studios:
            if item_details.studio == "":  # Just take the first one
                studio_name = studio["Name"]
                item_details.studio = studio_name
                break

    # Process Genres
    genres = item["Genres"]
    if genres is not None:
        for genre in genres:
            item_details.genre = item_details.genre  + " / " + genre

    # Process UserData
    userData = item["UserData"]

    if userData["Played"] == True:
        item_details.overlay = "6"
        item_details.play_count = 1
    else:
        item_details.overlay = "7"
        item_details.play_count = 0

    if userData["IsFavorite"] == True:
        item_details.overlay = "5"
        item_details.favorite = "true"
    else:
        item_details.favorite = "false"

    reasonableTicks = userData["PlaybackPositionTicks"]
    if reasonableTicks is not None:
        reasonableTicks = int(reasonableTicks) / 1000
        item_details.resume_time = int(reasonableTicks / 10000)

    item_details.series_name = item["SeriesName"]
    item_details.plot = item["Overview"]

    runtime = item["RunTimeTicks"]
    if item_details.is_folder == False and runtime is not None:
        item_details.duration = long(runtime) / 10000000

    child_count = item["ChildCount"]
    if child_count is not None:
        item_details.total_seasons = child_count

    recursive_item_count = item["RecursiveItemCount"]
    if recursive_item_count is not None:
        item_details.total_episodes = recursive_item_count

    unplayed_item_count = userData["UnplayedItemCount"]
    if unplayed_item_count is not None:
        item_details.unwatched_episodes = unplayed_item_count
        item_details.watched_episodes = item_details.total_episodes - unplayed_item_count

    item_details.number_episodes = item_details.total_episodes

    item_details.art = getArt(item, gui_options["server"])
    item_details.rating = item["OfficialRating"]
    item_details.critic_rating = item["CriticRating"]
    item_details.location_type = item["LocationType"]
    item_details.mpaa = item["OfficialRating"]
    item_details.recursive_item_count = item["RecursiveItemCount"]
    item_details.recursive_unplayed_items_count = userData["UnplayedItemCount"]

    item_details.mode = "GET_CONTENT"

    return item_details

def add_gui_item(url, item_details, display_options, folder=True):

    log.debug("Passed item_details: {0}", item_details.__dict__)

    if not item_details.name:
        return

    if item_details.mode:
        mode = "&mode=%s" % item_details.mode
    else:
        mode = "&mode=0"

    # Create the URL to pass to the item
    if folder:
        u = sys.argv[0] + "?url=" + urllib.quote(url) + mode + "&media_type=" + item_details.item_type
        if item_details.name_format:
            u += '&name_format=' + urllib.quote(item_details.name_format)
    else:
        u = sys.argv[0] + "?item_id=" + url + "&mode=PLAY"

    # Create the ListItem that will be displayed
    thumbPath = item_details.art["thumb"]

    listItemName = item_details.name

    # calculate percentage
    cappedPercentage = 0
    if item_details.resume_time > 0:
        duration = float(item_details.duration)
        if (duration > 0):
            resume = float(item_details.resume_time)
            percentage = int((resume / duration) * 100.0)
            cappedPercentage = percentage

    totalItems = item_details.total_episodes
    if totalItems != 0:
        watched = float(item_details.watched_episodes)
        percentage = int((watched / float(totalItems)) * 100.0)
        cappedPercentage = percentage

    countsAdded = False
    addCounts = display_options["addCounts"]
    if addCounts and item_details.unwatched_episodes != 0:
        countsAdded = True
        listItemName = listItemName + (" (%s)" % item_details.unwatched_episodes)

    addResumePercent = display_options["addResumePercent"]
    if (not countsAdded
            and addResumePercent
            and cappedPercentage not in [0, 100]):
        listItemName = listItemName + (" (%s%%)" % cappedPercentage)

    subtitle_available = display_options["addSubtitleAvailable"]
    if subtitle_available and item_details.subtitle_available:
        listItemName += " (cc)"

    if kodi_version > 17:
        list_item = xbmcgui.ListItem(listItemName, offscreen=True)
    else:
        list_item = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)

    log.debug("Setting thumbnail as: {0}", thumbPath)

    # calculate percentage
    if (cappedPercentage != 0):
        list_item.setProperty("complete_percentage", str(cappedPercentage))

    if folder == False:
        # list_item.setProperty('IsPlayable', 'true')
        list_item.setProperty('TotalTime', str(item_details.duration))
        list_item.setProperty('ResumeTime', str(item_details.resume_time))

    list_item.setArt(item_details.art)

    list_item.setProperty('fanart_image', item_details.art['fanart'])  # back compat
    list_item.setProperty('discart', item_details.art['discart'])  # not avail to setArt
    list_item.setProperty('tvshow.poster', item_details.art['tvshow.poster'])  # not avail to setArt

    # add context menu
    menu_items = add_context_menu(item_details, folder)
    if len(menu_items) > 0:
        list_item.addContextMenuItems(menu_items, True)

    # new way
    videoInfoLabels = {}

    # add cast
    if item_details.cast is not None:
        if kodi_version >= 17:
            list_item.setCast(item_details.cast)
        else:
            videoInfoLabels['cast'] = videoInfoLabels['castandrole'] = [(cast_member['name'], cast_member['role']) for cast_member in item_details.cast]

    videoInfoLabels["title"] = listItemName
    videoInfoLabels["plot"] = item_details.plot
    videoInfoLabels["Overlay"] = item_details.overlay
    videoInfoLabels["playcount"] = str(item_details.play_count)
    videoInfoLabels["TVShowTitle"] = item_details.series_name

    #if (extraData.get('type') == None or extraData.get('type') == "Video"):
    #    videoInfoLabels.update(details)
    #else:
    #    list_item.setInfo(type=extraData.get('type', 'Video'), infoLabels=details)

    videoInfoLabels["duration"] = item_details.duration
    videoInfoLabels["playcount"] = item_details.play_count
    if item_details.favorite == 'true':
        videoInfoLabels["top250"] = "1"

    videoInfoLabels["mpaa"] = item_details.mpaa
    videoInfoLabels["rating"] = item_details.rating
    videoInfoLabels["director"] = item_details.director
    videoInfoLabels["writer"] = item_details.writer
    videoInfoLabels["year"] = item_details.year
    videoInfoLabels["premiered"] = item_details.premiere_date
    videoInfoLabels["dateadded"] = item_details.date_added
    videoInfoLabels["studio"] = item_details.studio
    videoInfoLabels["genre"] = item_details.genre

    item_type = item_details.item_type.lower()
    mediatype = 'video'

    if item_type == 'movie' or item_type == 'boxset':
        mediatype = 'movie'
    elif item_type == 'series':
        mediatype = 'tvshow'
    elif item_type == 'season':
        mediatype = 'season'
    elif item_type == 'episode':
        mediatype = 'episode'
    elif item_type == 'audio' or item_type == 'musicalbum' or item_type == 'music':
        mediatype = 'song'

    videoInfoLabels["mediatype"] = mediatype

    if mediatype == 'episode':
        videoInfoLabels["episode"] = item_details.episode_number

    if (mediatype == 'season') or (mediatype == 'episode'):
        videoInfoLabels["season"] = item_details.season_number

    if item_type == 'musicalbum' or item_type == 'audio' or item_type == 'music':
        videoInfoLabels["tracknumber"] = item_details.track_number
        list_item.setInfo('music', videoInfoLabels)
    else:
        list_item.setInfo('video', videoInfoLabels)

    log.debug("videoInfoLabels: {0}", videoInfoLabels)

    list_item.addStreamInfo('video',
                            {'duration': item_details.duration,
                             'aspect': item_details.aspect_ratio,
                             'codec': item_details.video_codec,
                             'width': item_details.width,
                             'height': item_details.height})
    list_item.addStreamInfo('audio',
                            {'codec': item_details.audio_codec,
                             'channels': item_details.channels})

    if item_details.subtitle_lang != '':
        list_item.addStreamInfo('subtitle', {'language': item_details.subtitle_lang})

    list_item.setProperty('CriticRating', str(item_details.critic_rating))
    list_item.setProperty('ItemType', item_details.item_type)

    list_item.setProperty('TotalTime', str(item_details.duration))
    list_item.setProperty('TotalSeasons', str(item_details.total_seasons))
    list_item.setProperty('TotalEpisodes', str(item_details.total_episodes))
    list_item.setProperty('WatchedEpisodes', str(item_details.watched_episodes))
    list_item.setProperty('UnWatchedEpisodes', str(item_details.unwatched_episodes))
    list_item.setProperty('NumEpisodes', str(item_details.number_episodes))

    #list_item.setProperty('ItemGUID', extraData.get('guiid'))
    list_item.setProperty('id', item_details.id)

    return (u, list_item, folder)


def add_context_menu(item_details, folder):
    commands = []

    if item_details.id is None:
        return commands

    scriptToRun = PLUGINPATH + "/default.py"

    if item_details.item_type == "Season" or item_details.item_type == "MusicAlbum":
        argsToPass = "?mode=PLAY&item_id=" + item_details.id
        commands.append((i18n('play_all'), "RunPlugin(plugin://plugin.video.embycon" + argsToPass + ")"))

    if not folder:
        argsToPass = "?mode=PLAY&item_id=" + item_details.id + "&force_transcode=true"
        commands.append((i18n('emby_force_transcode'), "RunPlugin(plugin://plugin.video.embycon" + argsToPass + ")"))

    if not folder and item_details.item_type == "Movie":
        argsToPass = "?mode=playTrailer&id=" + item_details.id
        commands.append((i18n('play_trailer'), "RunPlugin(plugin://plugin.video.embycon" + argsToPass + ")"))

    # watched/unwatched
    if item_details.play_count == 0:
        argsToPass = 'markWatched,' + item_details.id
        commands.append((i18n('emby_mark_watched'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))
    else:
        argsToPass = 'markUnwatched,' + item_details.id
        commands.append((i18n('emby_mark_unwatched'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

    # favourite add/remove
    if item_details.favorite == 'false':
        argsToPass = 'markFavorite,' + item_details.id
        commands.append((i18n('emby_set_favorite'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))
    else:
        argsToPass = 'unmarkFavorite,' + item_details.id
        commands.append((i18n('emby_unset_favorite'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

    # delete
    argsToPass = 'delete,' + item_details.id
    commands.append((i18n('emby_delete'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

    return commands


def get_next_episode(item):

    if item.get("Type", "na") != "Episode":
        log.debug("Not an episode, can not get next")
        return None

    parendId = item.get("ParentId", "na")
    item_index = item.get("IndexNumber", -1)

    if parendId == "na":
        log.debug("No parent id, can not get next")
        return None

    if item_index == -1:
        log.debug("No episode number, can not get next")
        return None

    url = ( '{server}/emby/Users/{userid}/Items?' +
            '?Recursive=true' +
            '&ParentId=' + parendId +
            '&IsVirtualUnaired=false' +
            '&IsMissing=False' +
            '&IncludeItemTypes=Episode' +
            '&ImageTypeLimit=1' +
            '&format=json')

    data_manager = DataManager()
    items_result = data_manager.GetContent(url)
    log.debug("get_next_episode, sibling list: {0}", items_result)

    if items_result is None:
        log.debug("get_next_episode no results")
        return None

    item_list = items_result.get("Items", [])

    for item in item_list:
        index = item.get("IndexNumber", -1)
        # find the very next episode in the season
        if index == item_index + 1:
            log.debug("get_next_episode, found next episode: {0}", item)
            return item

    return None

