
import sys
import os
import urllib

import xbmc
import xbmcaddon
import xbmcgui

from utils import getArt
from simple_logging import SimpleLogging
from translation import i18n
from downloadutils import DownloadUtils

log = SimpleLogging(__name__)
kodi_version = int(xbmc.getInfoLabel('System.BuildVersion')[:2])

addon_instance = xbmcaddon.Addon(id='plugin.video.embycon')
addon_path = addon_instance.getAddonInfo('path')
PLUGINPATH = xbmc.translatePath(os.path.join(addon_path))

downloadUtils = DownloadUtils()

def extract_item_info(item, gui_options):

    id = item.get("Id")
    isFolder = item.get("IsFolder")

    item_type = item.get("Type")

    # set the episode number
    tempEpisode = ""
    if item_type == "Episode":
        tempEpisode = item.get("IndexNumber")
        if tempEpisode is not None:
            if tempEpisode < 10:
                tempEpisode = "0" + str(tempEpisode)
            else:
                tempEpisode = str(tempEpisode)
        else:
            tempEpisode = ""

    # set the season number
    tempSeason = None
    if item_type == "Episode":
        tempSeason = item.get("ParentIndexNumber")
    elif item_type == "Season":
        tempSeason = item.get("IndexNumber")
    if tempSeason is not None:
        if tempSeason < 10:
            tempSeason = "0" + str(tempSeason)
        else:
            tempSeason = str(tempSeason)
    else:
        tempSeason = ""

    # set the item name
    # override with name format string from request
    name_format = gui_options["name_format"]
    name_format_type = gui_options["name_format_type"]
    add_season_number = gui_options["add_season_number"]
    add_episode_number = gui_options["add_episode_number"]

    if name_format is not None and item.get("Type", "") == name_format_type:
        nameInfo = {}
        nameInfo["ItemName"] = item.get("Name", "").encode('utf-8')
        nameInfo["SeriesName"] = item.get("SeriesName", "").encode('utf-8')
        nameInfo["SeasonIndex"] = tempSeason
        nameInfo["EpisodeIndex"] = tempEpisode
        log.debug("FormatName : %s | %s" % (name_format, nameInfo))
        tempTitle = name_format.format(**nameInfo).strip()

    else:
        if (item.get("Name") != None):
            tempTitle = item.get("Name").encode('utf-8')
        else:
            tempTitle = i18n('missing_title')

        if item.get("Type") == "Episode":
            prefix = ''
            if add_season_number:
                prefix = "S" + str(tempSeason)
                if add_episode_number:
                    prefix = prefix + "E"
            if add_episode_number:
                prefix = prefix + str(tempEpisode)
            if prefix != '':
                tempTitle = prefix + ' - ' + tempTitle

    production_year = item.get("ProductionYear")
    if not production_year and item.get("PremiereDate"):
        production_year = int(item.get("PremiereDate")[:4])

    premiere_date = ""
    if item.get("PremiereDate") != None:
        tokens = (item.get("PremiereDate")).split("T")
        premiere_date = tokens[0]

    try:
        date_added = item['DateCreated']
        date_added = date_added.split('.')[0].replace('T', " ")
    except KeyError:
        date_added = ""

    # add the premiered date for Upcoming TV
    if item.get("LocationType") == "Virtual":
        airtime = item.get("AirTime")
        tempTitle = tempTitle + ' - ' + str(premiere_date) + ' - ' + str(airtime)

    # Process MediaStreams
    channels = ''
    videocodec = ''
    audiocodec = ''
    height = ''
    width = ''
    aspectfloat = 0.0
    subtitle_lang = ''
    subtitle_available = False
    mediaStreams = item.get("MediaStreams")
    if (mediaStreams != None):
        for mediaStream in mediaStreams:
            if mediaStream.get("Type") == "Video":
                videocodec = mediaStream.get("Codec")
                height = str(mediaStream.get("Height"))
                width = str(mediaStream.get("Width"))
                aspectratio = mediaStream.get("AspectRatio")
                if aspectratio is not None and len(aspectratio) >= 3:
                    try:
                        aspectwidth, aspectheight = aspectratio.split(':')
                        aspectfloat = float(aspectwidth) / float(aspectheight)
                    except:
                        aspectfloat = 1.85
            if mediaStream.get("Type") == "Audio":
                audiocodec = mediaStream.get("Codec")
                channels = mediaStream.get("Channels")
            if mediaStream.get("Type") == "Subtitle":
                subtitle_available = True
                if mediaStream.get("Language") is not None:
                    subtitle_lang = mediaStream.get("Language")

    # Process People
    director = ''
    writer = ''
    cast = None
    people = item.get("People")
    if (people != None):
        cast = []
        for person in people:
            if (person.get("Type") == "Director"):
                director = director + person.get("Name") + ' '
            if (person.get("Type") == "Writing"):
                writer = person.get("Name")
            if (person.get("Type") == "Writer"):
                writer = person.get("Name")
            if (person.get("Type") == "Actor"):
                person_name = person.get("Name")
                person_role = person.get("Role")
                if person_role == None:
                    person_role = ''
                person_id = person.get("Id")
                person_tag = person.get("PrimaryImageTag")
                person_thumbnail = downloadUtils.imageUrl(person_id, "Primary", 0, 400, 400, person_tag, server = gui_options["server"])
                person = {"name": person_name, "role": person_role, "thumbnail": person_thumbnail}
                cast.append(person)

    # Process Studios
    studio = ""
    studios = item.get("Studios")
    if (studios != None):
        for studio_string in studios:
            if studio == "":  # Just take the first one
                temp = studio_string.get("Name")
                studio = temp.encode('utf-8')

    # Process Genres
    genre = ""
    genres = item.get("Genres")
    if (genres != None and genres != []):
        for genre_string in genres:
            if genre == "":  # Just take the first genre
                genre = genre_string
            elif genre_string != None:
                genre = genre + " / " + genre_string

    # Process UserData
    userData = item.get("UserData")
    overlay = "0"
    favorite = "false"
    seekTime = 0
    if (userData != None):
        if userData.get("Played") != True:
            overlay = "7"
            watched = "true"
        else:
            overlay = "6"
            watched = "false"

        if userData.get("IsFavorite") == True:
            overlay = "5"
            favorite = "true"
        else:
            favorite = "false"

        if userData.get("PlaybackPositionTicks") != None:
            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            seekTime = reasonableTicks / 10000

    playCount = 0
    if (userData != None and userData.get("Played") == True):
        playCount = 1
    # Populate the details list
    details = {'title': tempTitle,
               'plot': item.get("Overview"),
               'Overlay': overlay,
               'playcount': str(playCount),
               # 'aired'       : episode.get('originallyAvailableAt','') ,
               'TVShowTitle': item.get("SeriesName"),
               }

    if item_type == "Episode":
        details['episode'] = tempEpisode
    if item_type == "Episode" or item_type == "Season":
        details['season'] = tempSeason

    tempDuration = 0
    if isFolder == False:
        try:
            tempDuration = long(item.get("RunTimeTicks", "0")) / 10000000
        except TypeError:
            tempDuration = 0

    TotalSeasons = 0 if item.get("ChildCount") == None else item.get("ChildCount")
    TotalEpisodes = 0 if item.get("RecursiveItemCount") == None else item.get("RecursiveItemCount")
    WatchedEpisodes = 0 if userData.get("UnplayedItemCount") == None else TotalEpisodes - userData.get("UnplayedItemCount")
    UnWatchedEpisodes = 0 if userData.get("UnplayedItemCount") == None else userData.get("UnplayedItemCount")
    NumEpisodes = TotalEpisodes

    art = getArt(item, gui_options["server"])
    # Populate the extraData list
    extraData = {'thumb': art['thumb'],
                 'fanart': art['fanart'],
                 'poster': art['poster'],
                 'banner': art['banner'],
                 'clearlogo': art['clearlogo'],
                 'discart': art['discart'],
                 'clearart': art['clearart'],
                 'landscape': art['landscape'],
                 'tvshow.poster': art['tvshow.poster'],
                 'tvshow.clearart': art['tvshow.clearart'],
                 'tvshow.banner': art['tvshow.banner'],
                 'tvshow.landscape': art['tvshow.landscape'],
                 'id': id,
                 'mpaa': item.get("OfficialRating"),
                 'rating': item.get("CommunityRating"),
                 'criticrating': item.get("CriticRating"),
                 'year': production_year,
                 'premieredate': premiere_date,
                 'dateadded': date_added,
                 'locationtype': item.get("LocationType"),
                 'studio': studio,
                 'genre': genre,
                 'playcount': playCount,
                 'director': director,
                 'writer': writer,
                 'channels': channels,
                 'videocodec': videocodec,
                 'aspectratio': str(aspectfloat),
                 'audiocodec': audiocodec,
                 'height': height,
                 'width': width,
                 'cast': cast,
                 'favorite': favorite,
                 'resumetime': str(seekTime),
                 'totaltime': tempDuration,
                 'duration': tempDuration,
                 'RecursiveItemCount': item.get("RecursiveItemCount"),
                 'RecursiveUnplayedItemCount': userData.get("UnplayedItemCount"),
                 'TotalSeasons': TotalSeasons,
                 'TotalEpisodes': TotalEpisodes,
                 'WatchedEpisodes': WatchedEpisodes,
                 'UnWatchedEpisodes': UnWatchedEpisodes,
                 'NumEpisodes': NumEpisodes,
                 'OriginalTitle': item.get("Name").encode('utf-8'),
                 'itemtype': item_type,
                 'SubtitleLang': subtitle_lang,
                 'SubtitleAvailable': subtitle_available}

    extraData["Path"] = item.get("Path")
    extraData['mode'] = "GET_CONTENT"

    return details, extraData

def add_gui_item(url, details, extraData, display_options, folder=True):

    url = url.encode('utf-8')

    log.debug("Adding GuiItem for [%s]" % details.get('title', i18n('unknown')))
    log.debug("Passed details: " + str(details))
    log.debug("Passed extraData: " + str(extraData))

    if details.get('title', '') == '':
        return

    if extraData.get('mode', None) is None:
        mode = "&mode=0"
    else:
        mode = "&mode=%s" % extraData['mode']

    # Create the URL to pass to the item
    if folder:
        u = sys.argv[0] + "?url=" + urllib.quote(url) + mode + "&media_type=" + extraData["itemtype"]
        if extraData.get("name_format"):
            u += '&name_format=' + urllib.quote(extraData.get("name_format"))
    else:
        u = sys.argv[0] + "?item_id=" + url + "&mode=PLAY"

    # Create the ListItem that will be displayed
    thumbPath = str(extraData.get('thumb', ''))

    listItemName = details.get('title', i18n('unknown'))

    # calculate percentage
    cappedPercentage = 0
    if (extraData.get('resumetime') != None and int(extraData.get('resumetime')) > 0):
        duration = float(extraData.get('duration'))
        if (duration > 0):
            resume = float(extraData.get('resumetime'))
            percentage = int((resume / duration) * 100.0)
            cappedPercentage = percentage

    totalItems = extraData["TotalEpisodes"]
    if totalItems != 0:
        watched = float(extraData["WatchedEpisodes"])
        percentage = int((watched / float(totalItems)) * 100.0)
        cappedPercentage = percentage

    countsAdded = False
    addCounts = display_options.get("addCounts", True)
    if addCounts and extraData["UnWatchedEpisodes"] != 0:
        countsAdded = True
        listItemName = listItemName + (" (%s)" % extraData["UnWatchedEpisodes"])

    addResumePercent = display_options.get("addResumePercent", True)
    if (countsAdded == False
            and addResumePercent
            and details.get('title') != None
            and cappedPercentage not in [0, 100]):
        listItemName = listItemName + (" (%s)" % cappedPercentage)

    subtitle_available = display_options.get("addSubtitleAvailable", False)
    if subtitle_available and extraData.get("SubtitleAvailable", False):
        listItemName += " (cc)"

    # update title with new name, this sets the new name in the deailts that are later passed to video info
    details['title'] = listItemName

    if kodi_version > 17:
        list_item = xbmcgui.ListItem(listItemName, offscreen=True)
    else:
        list_item = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)

    log.debug("Setting thumbnail as " + thumbPath)

    # calculate percentage
    if (cappedPercentage != 0):
        list_item.setProperty("complete_percentage", str(cappedPercentage))

    # For all end items
    if (not folder):
        # list_item.setProperty('IsPlayable', 'true')
        if extraData.get('type', 'video').lower() == "video":
            list_item.setProperty('TotalTime', str(extraData["duration"]))
            list_item.setProperty('ResumeTime', str(int(extraData.get('resumetime'))))

    # StartPercent

    artTypes = ['thumb', 'poster', 'fanart', 'clearlogo', 'discart', 'banner', 'clearart',
                'landscape', 'tvshow.poster', 'tvshow.clearart', 'tvshow.banner', 'tvshow.landscape']
    artLinks = {}
    for artType in artTypes:
        artLinks[artType] = extraData.get(artType, '')
        log.debug("Setting " + artType + " as " + artLinks[artType])
    list_item.setProperty('fanart_image', artLinks['fanart'])  # back compat
    list_item.setProperty('discart', artLinks['discart'])  # not avail to setArt
    list_item.setProperty('tvshow.poster', artLinks['tvshow.poster'])  # not avail to setArt
    list_item.setArt(artLinks)

    menuItems = add_context_menu(details, extraData, folder)
    if (len(menuItems) > 0):
        list_item.addContextMenuItems(menuItems, True)

    # new way
    videoInfoLabels = {}

    # add cast
    people = extraData.get('cast')
    if people is not None:
        if kodi_version >= 17:
            list_item.setCast(people)
        else:
            videoInfoLabels['cast'] = videoInfoLabels['castandrole'] = [(cast_member['name'], cast_member['role']) for cast_member in people]

    if (extraData.get('type') == None or extraData.get('type') == "Video"):
        videoInfoLabels.update(details)
    else:
        list_item.setInfo(type=extraData.get('type', 'Video'), infoLabels=details)

    videoInfoLabels["duration"] = extraData["duration"]
    videoInfoLabels["playcount"] = extraData["playcount"]
    if (extraData.get('favorite') == 'true'):
        videoInfoLabels["top250"] = "1"

    videoInfoLabels["mpaa"] = extraData['mpaa']
    videoInfoLabels["rating"] = extraData['rating']
    videoInfoLabels["director"] = extraData['director']
    videoInfoLabels["writer"] = extraData['writer']
    videoInfoLabels["year"] = extraData['year']
    videoInfoLabels["premiered"] = extraData['premieredate']
    videoInfoLabels["dateadded"] = extraData['dateadded']
    videoInfoLabels["studio"] = extraData['studio']
    videoInfoLabels["genre"] = extraData['genre']

    item_type = extraData.get('itemtype').lower()
    mediatype = 'video'

    if item_type == 'movie' or item_type == 'boxset':
        mediatype = 'movie'
    elif item_type == 'series':
        mediatype = 'tvshow'
    elif item_type == 'season':
        mediatype = 'season'
    elif item_type == 'episode':
        mediatype = 'episode'

    videoInfoLabels["mediatype"] = mediatype

    if mediatype == 'episode':
        videoInfoLabels["episode"] = details.get('episode')

    if (mediatype == 'season') or (mediatype == 'episode'):
        videoInfoLabels["season"] = details.get('season')

    list_item.setInfo('video', videoInfoLabels)

    list_item.addStreamInfo('video',
                            {'duration': extraData['duration'],
                             'aspect': extraData['aspectratio'],
                             'codec': extraData['videocodec'],
                             'width': extraData['width'],
                             'height': extraData['height']})
    list_item.addStreamInfo('audio',
                            {'codec': extraData['audiocodec'],
                             'channels': extraData['channels']})
    sub_lang = extraData.get('SubtitleLang', '')
    if sub_lang != '':
        list_item.addStreamInfo('subtitle', {'language': sub_lang})

    list_item.setProperty('CriticRating', str(extraData.get('criticrating')))
    list_item.setProperty('ItemType', extraData.get('itemtype'))

    list_item.setProperty('TotalTime', str(extraData["totaltime"]))
    list_item.setProperty('TotalSeasons', str(extraData["TotalSeasons"]))
    list_item.setProperty('TotalEpisodes', str(extraData["TotalEpisodes"]))
    list_item.setProperty('WatchedEpisodes', str(extraData["WatchedEpisodes"]))
    list_item.setProperty('UnWatchedEpisodes', str(extraData["UnWatchedEpisodes"]))
    list_item.setProperty('NumEpisodes', str(extraData["NumEpisodes"]))

    #list_item.setProperty('ItemGUID', extraData.get('guiid'))
    list_item.setProperty('id', extraData.get('id'))

    return (u, list_item, folder)


def add_context_menu(details, extraData, folder):
    commands = []

    item_id = extraData.get('id')
    if item_id != None:
        scriptToRun = PLUGINPATH + "/default.py"

        if not folder:
            argsToPass = "?mode=PLAY&item_id=" + item_id + "&force_transcode=true"
            commands.append((i18n('emby_force_transcode'), "RunPlugin(plugin://plugin.video.embycon" + argsToPass + ")"))

        if not folder and extraData.get("itemtype", "") == "Movie":
            argsToPass = "?mode=playTrailer&id=" + item_id
            commands.append((i18n('play_trailer'), "RunPlugin(plugin://plugin.video.embycon" + argsToPass + ")"))

        # watched/unwatched
        if extraData.get("playcount") == "0":
            argsToPass = 'markWatched,' + item_id
            commands.append((i18n('emby_mark_watched'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        elif extraData.get("playcount"):
            argsToPass = 'markUnwatched,' + item_id
            commands.append((i18n('emby_mark_unwatched'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

        # favourite add/remove
        if extraData.get('favorite') == 'false':
            argsToPass = 'markFavorite,' + item_id
            commands.append((i18n('emby_set_favorite'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        elif extraData.get('favorite') == 'true':
            argsToPass = 'unmarkFavorite,' + item_id
            commands.append((i18n('emby_unset_favorite'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

        # delete
        argsToPass = 'delete,' + item_id
        commands.append((i18n('emby_delete'), "RunScript(" + scriptToRun + ", " + argsToPass + ")"))

    return (commands)

