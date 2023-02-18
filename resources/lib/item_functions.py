from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import sys

from dateutil import tz
from six import ensure_text
from six.moves.urllib.parse import quote
import xbmcgui

from .utils import (
    datetime_from_string, get_art_url, image_url, get_current_datetime
)
from .lazylogger import LazyLogger

log = LazyLogger(__name__)


class ItemDetails:

    name = None
    sort_name = None
    id = None
    etag = None
    path = None
    is_folder = False
    plot = None
    series_name = None
    episode_number = 0
    season_number = 0
    episode_sort_number = 0
    season_sort_number = 0
    track_number = 0
    series_id = None
    art = None

    mpaa = None
    rating = None
    critic_rating = 0.0
    community_rating = 0.0
    year = None
    premiere_date = ""
    date_added = ""
    location_type = None
    studio = None
    production_location = None
    genres = None
    play_count = 0
    director = ""
    writer = ""
    cast = None
    tagline = ""
    status = None
    media_streams = None
    tags = None

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
    subtitle_available = False
    total_items = 0

    song_artist = ""
    album_artist = ""
    album_name = ""

    program_channel_name = None
    program_end_date = None
    program_start_date = None

    favorite = "false"
    overlay = "0"

    name_format = ""
    mode = ""

    baseline_itemname = None


def extract_item_info(item, gui_options):

    item_details = ItemDetails()

    item_details.id = item.get("Id")
    item_details.etag = item.get("Etag")
    item_details.is_folder = item.get("IsFolder")
    item_details.item_type = item.get("Type")
    item_details.location_type = item.get("LocationType")
    item_details.name = item.get("Name")
    item_details.sort_name = item.get("SortName")
    item_details.original_title = item_details.name

    if item_details.item_type == "Episode":
        item_details.episode_number = item.get("IndexNumber")
        item_details.season_number = item.get("ParentIndexNumber")
        item_details.series_id = item.get("SeriesId")

        if item_details.season_number != 0:
            item_details.season_sort_number = item_details.season_number
            item_details.episode_sort_number = item_details.episode_number
        else:
            special_after_season = item.get("AirsAfterSeasonNumber")
            special_before_season = item.get("AirsBeforeSeasonNumber")
            special_before_episode = item.get("AirsBeforeEpisodeNumber")

            if special_after_season:
                item_details.season_sort_number = special_after_season + 1
            elif special_before_season:
                item_details.season_sort_number = special_before_season - 1

            if special_before_episode:
                item_details.episode_sort_number = special_before_episode - 1

    elif item_details.item_type == "Season":
        item_details.season_number = item.get("IndexNumber")
        item_details.series_id = item.get("SeriesId")

    elif item_details.item_type == "Series":
        item_details.status = item.get("Status")

    elif item_details.item_type == "Audio":
        item_details.track_number = item.get("IndexNumber")
        item_details.album_name = item.get("Album")
        artists = item.get("Artists", [])
        if artists:
            item_details.song_artist = artists[0]  # get first artist

    elif item_details.item_type == "MusicAlbum":
        item_details.album_artist = item.get("AlbumArtist")
        item_details.album_name = item_details.name

    if item_details.season_number is None:
        item_details.season_number = 0
    if item_details.episode_number is None:
        item_details.episode_number = 0

    if item.get("Taglines", []):
        item_details.tagline = item.get("Taglines")[0]

    item_details.tags = []
    if item.get("TagItems", []):
        for tag_info in item.get("TagItems"):
            item_details.tags.append(tag_info.get("Name"))

    # set the item name
    # override with name format string from request
    name_format = gui_options.get("name_format")
    name_format_type = gui_options.get("name_format_type")

    if name_format is not None and item_details.item_type == name_format_type:
        name_info = {}
        name_info["ItemName"] = item.get("Name")
        season_name = item.get("SeriesName")
        if season_name:
            name_info["SeriesName"] = season_name
        else:
            name_info["SeriesName"] = ""
        name_info["SeasonIndex"] = u"%02d" % item_details.season_number
        name_info["EpisodeIndex"] = u"%02d" % item_details.episode_number
        log.debug("FormatName: {0} | {1}".format(name_format, name_info))
        item_details.name = ensure_text(name_format).format(**name_info).strip()

    year = item.get("ProductionYear")
    prem_date = item.get("PremiereDate")

    if year is not None:
        item_details.year = year
    elif item_details.year is None and prem_date is not None:
        item_details.year = int(prem_date[:4])

    if prem_date is not None:
        tokens = prem_date.split("T")
        item_details.premiere_date = tokens[0]

    create_date = item.get("DateCreated")
    if create_date:
        item_details.date_added = create_date.split('.')[0].replace('T', " ")

    # add the premiered date for Upcoming TV
    if item_details.location_type == "Virtual":
        airtime = item.get("AirTime")
        item_details.name = item_details.name + ' - ' + item_details.premiere_date + ' - ' + str(airtime)

    if item_details.item_type == "Program":
        item_details.program_channel_name = item.get("ChannelName")
        item_details.program_start_date = item.get("StartDate")
        item_details.program_end_date = item.get("EndDate")

    # Process MediaStreams
    media_streams = item.get("MediaStreams", [])
    if media_streams:
        media_info_list = []
        for mediaStream in media_streams:
            stream_type = mediaStream.get("Type")
            if stream_type == "Video":
                media_info = {}
                media_info["type"] = "video"
                media_info["codec"] = mediaStream.get("Codec")
                media_info["height"] = mediaStream.get("Height")
                media_info["width"] = mediaStream.get("Width")
                aspect_ratio = mediaStream.get("AspectRatio")
                media_info["aspect"] = aspect_ratio
                if aspect_ratio and len(aspect_ratio) >= 3:
                    try:
                        aspect_width, aspect_height = aspect_ratio.split(':')
                        media_info["apect_ratio"] = float(aspect_width) / float(aspect_height)
                    except:  # noqa
                        media_info["apect_ratio"] = 1.85
                else:
                    media_info["apect_ratio"] = 1.85
                media_info_list.append(media_info)
            if stream_type == "Audio":
                media_info = {}
                media_info["type"] = "audio"
                media_info["codec"] = mediaStream.get("Codec")
                media_info["channels"] = mediaStream.get("Channels")
                media_info["language"] = mediaStream.get("Language")
                media_info_list.append(media_info)
            if stream_type == "Subtitle":
                item_details.subtitle_available = True
                media_info = {}
                media_info["type"] = "sub"
                media_info["language"] = mediaStream.get("Language", '')
                media_info_list.append(media_info)

        item_details.media_streams = media_info_list

    # Process People
    people = item.get("People", [])
    if people is not None:
        cast = []
        for person in people:
            person_type = person.get("Type")
            if person_type == "Director":
                item_details.director = item_details.director + person.get("Name") + ' '
            elif person_type == "Writing":
                item_details.writer = person["Name"]
            elif person_type == "Actor":
                person_name = person.get("Name")
                person_role = person.get("Role")
                person_id = person.get("Id")
                person_tag = person.get("PrimaryImageTag")
                if person_tag:
                    person_thumbnail = image_url(person_id, "Primary", 0, 400,
                                                 400, person_tag,
                                                 server=gui_options["server"])
                else:
                    person_thumbnail = ""
                person = {"name": person_name, "role": person_role, "thumbnail": person_thumbnail}
                cast.append(person)
        item_details.cast = cast

    # Process Studios
    studios = item.get("Studios", [])
    if studios is not None:
        for studio in studios:
            if item_details.studio is None:  # Just take the first one
                studio_name = studio.get("Name")
                item_details.studio = studio_name
                break

    # production location
    prod_location = item.get("ProductionLocations", [])
    if prod_location:
        item_details.production_location = prod_location[0]

    # Process Genres
    genres = item.get("Genres", [])
    if genres:
        item_details.genres = genres

    # Process UserData
    user_data = item.get("UserData", {})

    if user_data.get("Played"):
        item_details.overlay = "6"
        item_details.play_count = 1
    else:
        item_details.overlay = "7"
        item_details.play_count = 0

    if user_data.get("IsFavorite"):
        item_details.overlay = "5"
        item_details.favorite = "true"
    else:
        item_details.favorite = "false"

    reasonable_ticks = user_data.get("PlaybackPositionTicks", 0)
    if reasonable_ticks:
        reasonable_ticks = int(reasonable_ticks) / 1000
        item_details.resume_time = int(reasonable_ticks / 10000)

    item_details.series_name = item.get("SeriesName", '')
    item_details.plot = item.get("Overview", '')

    runtime = item.get("RunTimeTicks")
    if item_details.is_folder is False and runtime:
        item_details.duration = runtime / 10000000

    child_count = item.get("ChildCount")
    if child_count:
        item_details.total_seasons = child_count

    recursive_item_count = item.get("RecursiveItemCount")
    if recursive_item_count:
        item_details.total_episodes = recursive_item_count

    unplayed_item_count = user_data.get("UnplayedItemCount")
    if unplayed_item_count is not None:
        item_details.unwatched_episodes = unplayed_item_count
        item_details.watched_episodes = item_details.total_episodes - unplayed_item_count

    item_details.number_episodes = item_details.total_episodes

    item_details.art = get_art(item, gui_options["server"])
    item_details.rating = item.get("OfficialRating")
    item_details.mpaa = item.get("OfficialRating")

    item_details.community_rating = item.get("CommunityRating")
    if not item_details.community_rating:
        item_details.community_rating = 0.0

    item_details.critic_rating = item.get("CriticRating")
    if not item_details.critic_rating:
        item_details.critic_rating = 0.0

    item_details.location_type = item.get("LocationType")
    item_details.recursive_item_count = item.get("RecursiveItemCount")
    item_details.recursive_unplayed_items_count = user_data.get("UnplayedItemCount")

    item_details.mode = "GET_CONTENT"

    return item_details


def add_gui_item(url, item_details, display_options, folder=True, default_sort=False):

    if not item_details.name:
        return None

    if item_details.mode:
        mode = "&mode=%s" % item_details.mode
    else:
        mode = "&mode=0"

    # Create the URL to pass to the item
    if folder:
        u = sys.argv[0] + "?url=" + quote(url) + mode + "&media_type=" + item_details.item_type
        if item_details.name_format:
            u += '&name_format=' + quote(item_details.name_format)
        if default_sort:
            u += '&sort=none'
    else:
        u = sys.argv[0] + "?item_id=" + url + "&mode=PLAY"

    list_item_name = item_details.name
    item_type = item_details.item_type.lower()
    is_video = item_type not in ['musicalbum', 'audio', 'music']

    # calculate percentage
    capped_percentage = 0
    if item_details.resume_time > 0:
        duration = float(item_details.duration)
        if duration > 0:
            resume = float(item_details.resume_time)
            percentage = int((resume / duration) * 100.0)
            capped_percentage = percentage

    total_items = item_details.total_episodes
    if total_items != 0:
        watched = float(item_details.watched_episodes)
        percentage = int((watched / float(total_items)) * 100.0)
        capped_percentage = percentage

    counts_added = False
    add_counts = display_options["addCounts"]
    if add_counts and item_details.unwatched_episodes != 0:
        counts_added = True
        list_item_name = list_item_name + (" (%s)" % item_details.unwatched_episodes)

    add_resume_percent = display_options["addResumePercent"]
    if (not counts_added
            and add_resume_percent
            and capped_percentage not in [0, 100]):
        list_item_name = list_item_name + (" (%s%%)" % capped_percentage)

    subtitle_available = display_options["addSubtitleAvailable"]
    if subtitle_available and item_details.subtitle_available:
        list_item_name += " (cc)"

    if item_details.item_type == "Program":
        start_time = datetime_from_string(item_details.program_start_date)
        end_time = datetime_from_string(item_details.program_end_date)

        duration = (end_time - start_time).total_seconds()
        now = get_current_datetime()
        time_done = (now - start_time).total_seconds()
        percentage_done = (float(time_done) / float(duration)) * 100.0
        capped_percentage = int(percentage_done)

        # Convert dates to local timezone for display
        local = tz.tzlocal()
        start_time_string = start_time.astimezone(local).strftime("%H:%M")
        end_time_string = end_time.astimezone(local).strftime("%H:%M")

        item_details.duration = int(duration)
        item_details.resume_time = int(time_done)

        if item_details.program_channel_name:
            list_item_name = '{} - {} - {} to {} ({}%)'.format(
                item_details.program_channel_name, list_item_name,
                start_time_string, end_time_string, capped_percentage)
        else:
            list_item_name = '{} - {} to {} ({}%)'.format(
                list_item_name, start_time_string, end_time_string,
                capped_percentage)

        time_info = "Start : " + start_time_string + "\n"
        time_info += "End : " + end_time_string + "\n"
        time_info += "Complete : " + str(int(percentage_done)) + "%\n"
        if item_details.plot:
            item_details.plot = time_info + item_details.plot
        else:
            item_details.plot = time_info

    list_item = xbmcgui.ListItem(list_item_name, offscreen=True)

    item_properties = {}

    # calculate percentage
    if capped_percentage != 0:
        item_properties["complete_percentage"] = str(capped_percentage)

    item_properties["IsPlayable"] = 'false'

    if not folder and is_video:
        item_properties["TotalTime"] = str(item_details.duration)
        item_properties["ResumeTime"] = str(item_details.resume_time)

    list_item.setArt(item_details.art)

    item_properties["fanart_image"] = item_details.art['fanart']  # back compat
    item_properties["discart"] = item_details.art['discart']  # not avail to setArt
    item_properties["tvshow.poster"] = item_details.art['tvshow.poster']  # not avail to setArt

    if item_details.series_id:
        item_properties["series_id"] = item_details.series_id

    # new way
    info_labels = {}

    # add cast
    if item_details.cast:
        list_item.setCast(item_details.cast)

    info_labels["title"] = list_item_name
    if item_details.sort_name:
        info_labels["sorttitle"] = item_details.sort_name
    else:
        info_labels["sorttitle"] = list_item_name

    info_labels["duration"] = item_details.duration
    info_labels["playcount"] = item_details.play_count
    if item_details.favorite == 'true':
        info_labels["top250"] = "1"

    info_labels["rating"] = item_details.rating
    info_labels["year"] = item_details.year

    if item_details.genres:
        genres_list = []
        for genre in item_details.genres:
            genres_list.append(quote(genre.encode('utf8')))
        item_properties["genres"] = quote("|".join(genres_list))

        info_labels["genre"] = " / ".join(item_details.genres)

    mediatype = 'video'

    if item_type == 'movie':
        mediatype = 'movie'
    elif item_type == 'boxset':
        mediatype = 'set'
    elif item_type == 'series':
        mediatype = 'tvshow'
    elif item_type == 'season':
        mediatype = 'season'
    elif item_type == 'episode':
        mediatype = 'episode'
    elif item_type == 'musicalbum':
        mediatype = 'album'
    elif item_type == 'musicartist':
        mediatype = 'artist'
    elif item_type == 'audio' or item_type == 'music':
        mediatype = 'song'
    elif item_type == 'musicvideo':
        mediatype = 'musicvideo'

    info_labels["mediatype"] = mediatype

    if item_type == 'episode':
        info_labels["episode"] = item_details.episode_number
        info_labels["season"] = item_details.season_number
        info_labels["sortseason"] = item_details.season_sort_number
        info_labels["sortepisode"] = item_details.episode_sort_number
        info_labels["tvshowtitle"] = item_details.series_name
        if item_details.season_number == 0:
            item_properties["IsSpecial"] = "true"

    elif item_type == 'season':
        info_labels["season"] = item_details.season_number
        info_labels["episode"] = item_details.total_episodes
        info_labels["tvshowtitle"] = item_details.series_name
        if item_details.season_number == 0:
            item_properties["IsSpecial"] = "true"

    elif item_type == "series":
        info_labels["episode"] = item_details.total_episodes
        info_labels["season"] = item_details.total_seasons
        info_labels["status"] = item_details.status
        info_labels["tvshowtitle"] = item_details.name

    if is_video:

        info_labels["Overlay"] = item_details.overlay
        info_labels["tagline"] = item_details.tagline
        info_labels["studio"] = item_details.studio
        info_labels["premiered"] = item_details.premiere_date
        info_labels["plot"] = item_details.plot
        info_labels["director"] = item_details.director
        info_labels["writer"] = item_details.writer
        info_labels["dateadded"] = item_details.date_added
        info_labels["country"] = item_details.production_location
        info_labels["mpaa"] = item_details.mpaa
        info_labels["tag"] = item_details.tags

        if display_options["addUserRatings"]:
            info_labels["userrating"] = item_details.critic_rating

        if item_type in ('movie', 'series'):
            info_labels["trailer"] = "plugin://plugin.video.jellycon?mode=playTrailer&id=" + item_details.id

        list_item.setInfo('video', info_labels)

        if item_details.media_streams is not None:
            for stream in item_details.media_streams:
                if stream["type"] == "video":
                    list_item.addStreamInfo('video',
                                            {'duration': item_details.duration,
                                             'aspect': stream["apect_ratio"],
                                             'codec': stream["codec"],
                                             'width': stream["width"],
                                             'height': stream["height"]})
                elif stream["type"] == "audio":
                    list_item.addStreamInfo('audio',
                                            {'codec': stream["codec"],
                                             'channels': stream["channels"],
                                             'language': stream["language"]})
                elif stream["type"] == "sub":
                    list_item.addStreamInfo('subtitle',
                                            {'language': stream["language"]})

        item_properties["TotalSeasons"] = str(item_details.total_seasons)
        item_properties["TotalEpisodes"] = str(item_details.total_episodes)
        item_properties["NumEpisodes"] = str(item_details.number_episodes)

        list_item.setRating("imdb", item_details.community_rating, 0, True)
        item_properties["TotalTime"] = str(item_details.duration)

    else:
        info_labels["tracknumber"] = item_details.track_number
        if item_details.album_artist:
            info_labels["artist"] = item_details.album_artist
        elif item_details.song_artist:
            info_labels["artist"] = item_details.song_artist
        info_labels["album"] = item_details.album_name

        list_item.setInfo('music', info_labels)

    list_item.setContentLookup(False)
    item_properties["ItemType"] = item_details.item_type
    item_properties["id"] = item_details.id

    if item_details.baseline_itemname is not None:
        item_properties["suggested_from_watching"] = item_details.baseline_itemname

    list_item.setProperties(item_properties)

    return u, list_item, folder


def get_art(item, server):

    art = {
        'thumb': '',
        'fanart': '',
        'poster': '',
        'banner': '',
        'clearlogo': '',
        'clearart': '',
        'discart': '',
        'landscape': '',
        'tvshow.fanart': '',
        'tvshow.poster': '',
        'tvshow.clearart': '',
        'tvshow.clearlogo': '',
        'tvshow.banner': '',
        'tvshow.landscape': ''
    }

    image_tags = item.get("ImageTags", {})
    if image_tags and image_tags.get("Primary"):
        art['thumb'] = get_art_url(item, "Primary", server=server)

    item_type = item["Type"]

    if item_type == "Genre":
        art['poster'] = get_art_url(item, "Primary", server=server)
    elif item_type == "Episode":
        art['tvshow.poster'] = get_art_url(item, "Primary", parent=True, server=server)
        art['tvshow.clearart'] = get_art_url(item, "Art", parent=True, server=server)
        art['clearart'] = get_art_url(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = get_art_url(item, "Logo", parent=True, server=server)
        art['clearlogo'] = get_art_url(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = get_art_url(item, "Banner", parent=True, server=server)
        art['banner'] = get_art_url(item, "Banner", parent=True, server=server)
        art['tvshow.landscape'] = get_art_url(item, "Thumb", parent=True, server=server)
        art['landscape'] = get_art_url(item, "Thumb", parent=True, server=server)
        art['tvshow.fanart'] = get_art_url(item, "Backdrop", parent=True, server=server)
        art['fanart'] = get_art_url(item, "Backdrop", parent=True, server=server)
    elif item_type == "Season":
        art['tvshow.poster'] = get_art_url(item, "Primary", parent=True, server=server)
        art['season.poster'] = get_art_url(item, "Primary", parent=False, server=server)
        art['poster'] = get_art_url(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = get_art_url(item, "Art", parent=True, server=server)
        art['clearart'] = get_art_url(item, "Art", parent=True, server=server)
        art['tvshow.clearlogo'] = get_art_url(item, "Logo", parent=True, server=server)
        art['clearlogo'] = get_art_url(item, "Logo", parent=True, server=server)
        art['tvshow.banner'] = get_art_url(item, "Banner", parent=True, server=server)
        art['season.banner'] = get_art_url(item, "Banner", parent=False, server=server)
        art['banner'] = get_art_url(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = get_art_url(item, "Thumb", parent=True, server=server)
        art['season.landscape'] = get_art_url(item, "Thumb", parent=False, server=server)
        art['landscape'] = get_art_url(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = get_art_url(item, "Backdrop", parent=True, server=server)
        art['fanart'] = get_art_url(item, "Backdrop", parent=True, server=server)
    elif item_type == "Series":
        art['tvshow.poster'] = get_art_url(item, "Primary", parent=False, server=server)
        art['poster'] = get_art_url(item, "Primary", parent=False, server=server)
        art['tvshow.clearart'] = get_art_url(item, "Art", parent=False, server=server)
        art['clearart'] = get_art_url(item, "Art", parent=False, server=server)
        art['tvshow.clearlogo'] = get_art_url(item, "Logo", parent=False, server=server)
        art['clearlogo'] = get_art_url(item, "Logo", parent=False, server=server)
        art['tvshow.banner'] = get_art_url(item, "Banner", parent=False, server=server)
        art['banner'] = get_art_url(item, "Banner", parent=False, server=server)
        art['tvshow.landscape'] = get_art_url(item, "Thumb", parent=False, server=server)
        art['landscape'] = get_art_url(item, "Thumb", parent=False, server=server)
        art['tvshow.fanart'] = get_art_url(item, "Backdrop", parent=False, server=server)
        art['fanart'] = get_art_url(item, "Backdrop", parent=False, server=server)
    elif item_type == "Movie" or item_type == "BoxSet":
        art['poster'] = get_art_url(item, "Primary", server=server)
        art['landscape'] = get_art_url(item, "Thumb", server=server)
        art['banner'] = get_art_url(item, "Banner", server=server)
        art['clearlogo'] = get_art_url(item, "Logo", server=server)
        art['clearart'] = get_art_url(item, "Art", server=server)
        art['discart'] = get_art_url(item, "Disc", server=server)

    art['fanart'] = get_art_url(item, "Backdrop", server=server)
    if not art['fanart']:
        art['fanart'] = get_art_url(item, "Backdrop", parent=True, server=server)

    return art
