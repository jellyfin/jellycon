# Gnu General Public License - see LICENSE.TXT

import urllib
import encodings

import xbmc
import xbmcgui

from .loghandler import LazyLogger
from .datamanager import DataManager

from .translation import string_load

log = LazyLogger(__name__)
dataManager = DataManager()

details_string = 'EpisodeCount,SeasonCount,Path,Etag,MediaStreams'
icon = xbmc.translatePath('special://home/addons/plugin.video.jellycon/icon.png')


def not_found(content_string):
    xbmcgui.Dialog().notification('JellyCon', string_load(30305) % content_string, icon=icon, sound=False)


def playback_starting(content_string):
    xbmcgui.Dialog().notification('JellyCon', string_load(30306) % content_string, icon=icon, sound=False)


def search(item_type, query):
    content_url = ('{server}/Search/Hints?searchTerm=' + query +
                   '&IncludeItemTypes=' + item_type +
                   '&UserId={userid}'
                   '&StartIndex=0' +
                   '&Limit=25' +
                   '&IncludePeople=false&IncludeMedia=true&IncludeGenres=false&IncludeStudios=false&IncludeArtists=false')

    result = dataManager.get_content(content_url)
    return result


def get_items(video_type, item_id=None, parent_id=None):
    content_url = None
    result = dict()

    if video_type == 'season':
        content_url = ('{server}/Shows/' + item_id +
                       '/Seasons'
                       '?userId={userid}' +
                       '&Fields=' + details_string +
                       '&format=json')

    elif video_type == 'movie' or video_type == 'episode':
        content_url = ('{server}/Users/{userid}/items' +
                       '?ParentId=' + parent_id +
                       '&IsVirtualUnAired=false' +
                       '&IsMissing=false' +
                       '&Fields=' + details_string +
                       '&format=json')

    if content_url:
        result = dataManager.get_content(content_url)

    return result


def get_item(item_id):
    result = dataManager.get_content('{server}/Users/{userid}/Items/' + item_id + '?Fields=ProviderIds&format=json')
    return result


def get_imdb_id(item_id):
    item = get_item(item_id)
    imdb = item.get('ProviderIds', {}).get('Imdb')
    return imdb


def get_season_id(parent_id, season):
    season_items = get_items('season', parent_id)
    season_items = season_items.get('Items')

    if season_items is None:
        season_items = []

    for season_item in season_items:
        if season_item.get('IndexNumber') == int(season):
            season_id = season_item.get('Id')
            return season_id

    return None


def get_episode_id(parent_id, episode):
    episode_items = get_items('episode', parent_id=parent_id)
    episode_items = episode_items.get('Items')

    if episode_items is None:
        episode_items = []

    for episode_item in episode_items:
        if episode_item.get('IndexNumber') == int(episode):
            episode_id = episode_item.get('Id')
            return episode_id

    return None


def get_match(item_type, title, year, imdb_id):
    query = urllib.quote(title)

    results = search(item_type, query=query)
    results = results.get('SearchHints')
    if results is None:
        results = []
    log.debug('SearchHints jsonData: {0}'.format(results))

    potential_matches = []

    for item in results:
        name = item.get('Name')
        production_year = item.get('ProductionYear')
        if (name == title and int(year) == production_year) or (int(year) == production_year):
            potential_matches.append(item)

    log.debug('Potential matches: {0}'.format(potential_matches))

    for item in potential_matches:
        item_imdb_id = get_imdb_id(item.get('ItemId'))
        if item_imdb_id == imdb_id:
            log.debug('Found match: {0}'.format(item))
            return item

    return None


def entry_point(parameters):
    item_type = None
    action = parameters.get('action', None)
    video_type = parameters.get('video_type', None)

    title = urllib.unquote(parameters.get('title', ''))

    year = parameters.get('year', '')
    episode = parameters.get('episode', '')
    season = parameters.get('season', '')
    imdb_id = parameters.get('imdb_id', '')

    if video_type == 'show' or video_type == 'season' or video_type == 'episode':
        item_type = 'Series'
    elif video_type == 'movie':
        item_type = 'Movie'

    if not item_type:
        return

    match = get_match(item_type, title, year, imdb_id)

    if not match:
        title_search_word = ''
        title_words = title.split(' ')

        for word in title_words:
            if len(word) > len(title_search_word):
                title_search_word = word

        title_search_word = title_search_word.replace(':', '')

        if title_search_word:
            match = get_match(item_type, title_search_word, year, imdb_id)

    str_season = str(season)
    if len(str_season) == 1:
        str_season = '0' + str_season
    str_episode = str(episode)
    if len(str_episode) == 1:
        str_episode = '0' + str_episode

    if action == 'play':
        play_item_id = None

        if video_type == 'movie':
            if match:
                play_item_id = match.get('ItemId')

            if not play_item_id:
                not_found('{title} ({year})'.format(title=title, year=year))

        elif video_type == 'episode':
            if not season or not episode:
                return

            if match:
                item_id = match.get('ItemId')
                season_id = get_season_id(item_id, season)

                if season_id:
                    episode_id = get_episode_id(season_id, episode)
                    if episode_id:
                        play_item_id = episode_id

            if not play_item_id:
                not_found('{title} ({year}) - S{season}E{episode}'.format(title=title, year=year, season=str_season, episode=str_episode))

        if play_item_id:
            if video_type == 'episode':
                playback_starting('{title} ({year}) - S{season}E{episode}'.format(title=title, year=year, season=str_season, episode=str_episode))
            else:
                playback_starting('{title} ({year})'.format(title=title, year=year))
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.jellycon/?mode=PLAY&item_id={item_id})'.format(item_id=play_item_id))

    elif action == 'open':
        url = media_type = None

        if video_type == 'show':
            if match:
                item_id = match.get('ItemId')
                media_type = 'series'
                url = ('{server}/Shows/' + item_id +
                       '/Seasons'
                       '?userId={userid}' +
                       '&Fields=' + details_string +
                       '&format=json')

            if not url:
                not_found('{title} ({year})'.format(title=title, year=year))

        elif video_type == 'season':
            if not season:
                return

            if match:
                item_id = match.get('ItemId')
                season_id = get_season_id(item_id, season)

                if season_id:
                    media_type = 'episodes'

                    url = ('{server}/Users/{userid}/items' +
                           '?ParentId=' + season_id +
                           '&IsVirtualUnAired=false' +
                           '&IsMissing=false' +
                           '&Fields=' + details_string +
                           '&format=json')

            if not url:
                not_found('{title} ({year}) - S{season}'.format(title=title, year=year, season=str_season))

        if url and media_type:
            xbmc.executebuiltin('ActivateWindow(Videos, plugin://plugin.video.jellycon/?mode=GET_CONTENT&url={url}&media_type={media_type})'.format(url=urllib.quote(url), media_type=media_type))
