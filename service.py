# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcaddon
import xbmcgui
import time
import json
import traceback

from resources.lib.error import catch_except
from resources.lib.downloadutils import DownloadUtils
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import playFile
from resources.lib.kodi_utils import HomeWindow
from resources.lib.translation import i18n
from resources.lib.widgets import checkForNewContent
from resources.lib.websocket_client import WebSocketClient

# clear user and token when logging in
home_window = HomeWindow()
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log = SimpleLogging('service')
download_utils = DownloadUtils()

# auth the service
try:
    download_utils.authenticate()
except Exception as error:
    log.error("Error with initial service auth: {0}", error)


def hasData(data):
    if data is None or len(data) == 0 or data == "None":
        return False
    else:
        return True


def sendProgress():
    playing_file = xbmc.Player().getPlayingFile()
    play_data = monitor.played_information.get(playing_file)

    if play_data is None:
        return

    log.debug("Sending Progress Update")

    play_time = xbmc.Player().getTime()
    play_data["currentPossition"] = play_time

    item_id = play_data.get("item_id")
    if item_id is None:
        return

    ticks = int(play_time * 10000000)
    paused = play_data.get("paused", False)
    playback_type = play_data.get("playback_type")
    play_session_id = play_data.get("play_session_id")

    postdata = {
        'QueueableMediaTypes': "Video",
        'CanSeek': True,
        'ItemId': item_id,
        'MediaSourceId': item_id,
        'PositionTicks': ticks,
        'IsPaused': paused,
        'IsMuted': False,
        'PlayMethod': playback_type,
        'PlaySessionId': play_session_id
    }

    log.debug("Sending POST progress started: {0}", postdata)

    url = "{server}/emby/Sessions/Playing/Progress"
    download_utils.downloadUrl(url, postBody=postdata, method="POST")

@catch_except()
def promptForStopActions(item_id, current_possition):

    settings = xbmcaddon.Addon(id='plugin.video.embycon')

    prompt_next_percentage = int(settings.getSetting('promptPlayNextEpisodePercentage'))
    play_prompt = settings.getSetting('promptPlayNextEpisodePercentage_prompt') == "true"
    prompt_delete_episode_percentage = int(settings.getSetting('promptDeleteEpisodePercentage'))
    prompt_delete_movie_percentage = int(settings.getSetting('promptDeleteMoviePercentage'))

    # everything is off so return
    if (prompt_next_percentage == 100 and
            prompt_delete_episode_percentage == 100 and
            prompt_delete_movie_percentage == 100):
        return

    jsonData = download_utils.downloadUrl("{server}/emby/Users/{userid}/Items/" + item_id + "?format=json")
    result = json.loads(jsonData)
    prompt_to_delete = False
    runtime = result.get("RunTimeTicks", 0)

    # if no runtime we cant calculate perceantge so just return
    if runtime == 0:
        log.debug("No runtime so returing")
        return

    # item percentage complete
    percenatge_complete = int(((current_possition * 10000000) / runtime) * 100)
    log.debug("Episode Percentage Complete: {0}", percenatge_complete)

    if (prompt_delete_episode_percentage < 100 and
                result.get("Type", "na") == "Episode" and
                percenatge_complete > prompt_delete_episode_percentage):
            prompt_to_delete = True

    if (prompt_delete_movie_percentage < 100 and
                result.get("Type", "na") == "Movie" and
                percenatge_complete > prompt_delete_movie_percentage):
            prompt_to_delete = True

    if prompt_to_delete:
        log.debug("Prompting for delete")
        resp = xbmcgui.Dialog().yesno(i18n('confirm_file_delete'), i18n('file_delete_confirm'), autoclose=10000)
        if resp:
            log.debug("Deleting item: {0}", item_id)
            url = "{server}/emby/Items/%s?format=json" % item_id
            download_utils.downloadUrl(url, method="DELETE")
            xbmc.executebuiltin("Container.Refresh")

    # prompt for next episode
    if (prompt_next_percentage < 100 and
                result.get("Type", "na") == "Episode" and
                percenatge_complete > prompt_next_percentage):
        parendId = result.get("ParentId", "na")
        item_index = result.get("IndexNumber", -1)

        if parendId == "na":
            log.debug("No parent id, can not prompt for next episode")
            return

        if item_index == -1:
            log.debug("No episode number, can not prompt for next episode")
            return

        url = ( '{server}/emby/Users/{userid}/Items?' +
                '?Recursive=true' +
                '&ParentId=' + parendId +
                # '&Filters=IsUnplayed,IsNotFolder' +
                '&IsVirtualUnaired=false' +
                '&IsMissing=False' +
                '&IncludeItemTypes=Episode' +
                '&ImageTypeLimit=1' +
                '&format=json')

        jsonData = download_utils.downloadUrl(url)

        items_result = json.loads(jsonData)
        log.debug("Prompt Next Item Details: {0}", items_result)
        # find next episode
        item_list = items_result.get("Items", [])
        for item in item_list:
            index = item.get("IndexNumber", -1)
            if index == item_index + 1: # find the very next episode in the season

                resp = True
                if play_prompt:
                    next_epp_name = "%02d - %s" % (index, item.get("Name", "n/a"))
                    resp = xbmcgui.Dialog().yesno(i18n("play_next_title"), i18n("play_next_question"), next_epp_name, autoclose=10000)

                if resp:
                    next_item_id = item.get("Id")
                    log.debug("Playing Next Episode: {0}", next_item_id)

                    play_info = {}
                    play_info["item_id"] = next_item_id
                    play_info["auto_resume"] = "-1"
                    play_info["force_transcode"] = False
                    play_data = json.dumps(play_info)

                    home_window = HomeWindow()
                    home_window.setProperty("item_id", next_item_id)
                    home_window.setProperty("play_item_message", play_data)

                break

@catch_except()
def stopAll(played_information):
    if len(played_information) == 0:
        return

    log.debug("played_information: {0}", played_information)

    for item_url in played_information:
        data = played_information.get(item_url)
        if data is not None:
            log.debug("item_url: {0}", item_url)
            log.debug("item_data: {0}", data)

            current_possition = data.get("currentPossition", 0)
            emby_item_id = data.get("item_id")

            if hasData(emby_item_id):
                log.debug("Playback Stopped at: {0}", current_possition)

                url = "{server}/emby/Sessions/Playing/Stopped"
                postdata = {
                    'ItemId': emby_item_id,
                    'MediaSourceId': emby_item_id,
                    'PositionTicks': int(current_possition * 10000000)
                }
                download_utils.downloadUrl(url, postBody=postdata, method="POST")

                promptForStopActions(emby_item_id, current_possition)

    played_information.clear()


class Service(xbmc.Player):
    played_information = {}

    def __init__(self, *args):
        log.debug("Starting monitor service: {0}", args)
        self.played_information = {}

    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        stopAll(self.played_information)

        current_playing_file = xbmc.Player().getPlayingFile()
        log.debug("onPlayBackStarted: {0}", current_playing_file)

        home_window = HomeWindow()
        emby_item_id = home_window.getProperty("item_id")
        playback_type = home_window.getProperty("PlaybackType_" + emby_item_id)
        play_session_id = home_window.getProperty("PlaySessionId_" + emby_item_id)

        # if we could not find the ID of the current item then return
        if emby_item_id is None or len(emby_item_id) == 0:
            return

        log.debug("Sending Playback Started")
        postdata = {
            'QueueableMediaTypes': "Video",
            'CanSeek': True,
            'ItemId': emby_item_id,
            'MediaSourceId': emby_item_id,
            'PlayMethod': playback_type,
            'PlaySessionId': play_session_id
        }

        log.debug("Sending POST play started: {0}", postdata)

        url = "{server}/emby/Sessions/Playing"
        download_utils.downloadUrl(url, postBody=postdata, method="POST")

        data = {}
        data["item_id"] = emby_item_id
        data["paused"] = False
        data["playback_type"] = playback_type
        data["play_session_id"] = play_session_id
        self.played_information[current_playing_file] = data

        log.debug("ADDING_FILE: {0}", current_playing_file)
        log.debug("ADDING_FILE: {0}", self.played_information)

    def onPlayBackEnded(self):
        # Will be called when kodi stops playing a file
        log.debug("EmbyCon Service -> onPlayBackEnded")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    def onPlayBackStopped(self):
        # Will be called when user stops kodi playing a file
        log.debug("onPlayBackStopped")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    def onPlayBackPaused(self):
        # Will be called when kodi pauses the video
        log.debug("onPlayBackPaused")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = True
            sendProgress()

    def onPlayBackResumed(self):
        # Will be called when kodi resumes the video
        log.debug("onPlayBackResumed")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = False
            sendProgress()

    def onPlayBackSeek(self, time, seekOffset):
        # Will be called when kodi seeks in video
        log.debug("onPlayBackSeek")
        sendProgress()


monitor = Service()
home_window = HomeWindow()
last_progress_update = time.time()
last_content_check = time.time()
websocket_client = WebSocketClient()

# start the WbSocket Client running
settings = xbmcaddon.Addon(id='plugin.video.embycon')
remote_control = settings.getSetting('remoteControl') == "true"
if remote_control:
    websocket_client.start()

'''
def getNowPlaying():

    # Get the active player
    result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
    result = unicode(result, 'utf-8', errors='ignore')
    log.debug("Got active player: {0}", result)
    result = json.loads(result)

    if 'result' in result and len(result["result"]) > 0:
        playerid = result["result"][0]["playerid"]

        # Get details of the playing media
        log.debug("Getting details of now  playing media")
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str(
                playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount", "genre", "uniqueid"] } }')
        result = unicode(result, 'utf-8', errors='ignore')
        log.debug("playing_item_details: {0}", result)

        result = json.loads(result)
        return result
'''

# monitor.abortRequested() is causes issues, it currently triggers for all addon cancelations which causes
# the service to exit when a user cancels an addon load action. This is a bug in Kodi.
# I am switching back to xbmc.abortRequested approach until kodi is fixed or I find a work arround

while not xbmc.abortRequested:

    try:
        if xbmc.Player().isPlaying():
            # if playing every 10 seconds updated the server with progress
            if (time.time() - last_progress_update) > 10:
                last_progress_update = time.time()
                sendProgress()
        else:
            # if we have a play item them trigger playback
            play_data = home_window.getProperty("play_item_message")
            if play_data:
                home_window.clearProperty("play_item_message")
                play_info = json.loads(play_data)
                playFile(play_info)

            # if not playing every 60 seonds check for new widget content
            if (time.time() - last_content_check) > 60:
                last_content_check = time.time()
                checkForNewContent()

        #getNowPlaying()

    except Exception as error:
        log.error("Exception in Playback Monitor: {0}", error)
        log.error("{0}", traceback.format_exc())

    xbmc.sleep(1000)

# stop the WebSocket Client
websocket_client.stop_client()

# clear user and token when loggin off
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log.error("Service shutting down")
