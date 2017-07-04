# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcaddon
import xbmcgui
import time
import json
import platform

from resources.lib.downloadutils import DownloadUtils
from resources.lib.server_info import getServerId
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import playFile
from resources.lib.kodi_utils import HomeWindow
from resources.lib.translation import i18n
from resources.lib.ga_client import GoogleAnalytics, log_error

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
except Exception, e:
    pass


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

    log.info("Sending Progress Update")

    play_time = xbmc.Player().getTime()
    play_data["currentPossition"] = play_time

    item_id = play_data.get("item_id")
    if item_id is None:
        return

    ticks = int(play_time * 10000000)
    paused = play_data.get("paused", False)
    playback_type = play_data.get("playback_type")

    postdata = {
        'QueueableMediaTypes': "Video",
        'CanSeek': True,
        'ItemId': item_id,
        'MediaSourceId': item_id,
        'PositionTicks': ticks,
        'IsPaused': paused,
        'IsMuted': False,
        'PlayMethod': playback_type
    }

    log.debug("Sending POST progress started: %s." % postdata)

    url = "{server}/emby/Sessions/Playing/Progress"
    download_utils.downloadUrl(url, postBody=postdata, method="POST")

def promptForStopActions(item_id, current_possition):

    settings = xbmcaddon.Addon(id='plugin.video.embycon')

    prompt_next_percentage = int(settings.getSetting('promptPlayNextEpisodePercentage'))
    prompt_delete_episode_percentage = int(settings.getSetting('promptDeleteEpisodePercentage'))
    prompt_delete_movie_percentage = int(settings.getSetting('promptDeleteMoviePercentage'))

    # everything is off so return
    if prompt_next_percentage == 100 and prompt_delete_episode_percentage == 100 and prompt_delete_movie_percentage == 100:
        return

    jsonData = download_utils.downloadUrl("{server}/emby/Users/{userid}/Items/" +
                                          item_id + "?format=json",
                                          suppress=False, popup=1)
    result = json.loads(jsonData)
    prompt_to_delete = False
    runtime = result.get("RunTimeTicks", 0)

    # if no runtime we cant calculate perceantge so just return
    if runtime == 0:
        log.debug("No runtime so returing")
        return

    # item percentage complete
    percenatge_complete = int(((current_possition * 10000000) / runtime) * 100)
    log.debug("Episode Percentage Complete: %s" % percenatge_complete)

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
            log.debug("Deleting item: %s" % item_id)
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

        jsonData = download_utils.downloadUrl('{server}/emby/Users/{userid}/Items?' +
                             '?Recursive=true' +
                             '&ParentId=' + parendId +
                             #'&Filters=IsUnplayed,IsNotFolder' +
                             '&IsVirtualUnaired=false' +
                             '&IsMissing=False' +
                             '&IncludeItemTypes=Episode' +
                             '&ImageTypeLimit=1' +
                             '&format=json',
                              suppress=False, popup=1)

        items_result = json.loads(jsonData)
        log.debug("Prompt Next Item Details: %s" % items_result)
        # find next episode
        item_list = items_result.get("Items", [])
        for item in item_list:
            index = item.get("IndexNumber", -1)
            if index > item_index: # find the next episode in the season
                resp = xbmcgui.Dialog().yesno(i18n("play_next_title"), i18n("play_next_question"), autoclose=10000)
                if resp:
                    next_item_id = item.get("Id")
                    log.debug("Playing Next Episode: %s" % next_item_id)

                    play_info = {}
                    play_info["item_id"] = next_item_id
                    play_info["auto_resume"] = "-1"
                    play_info["force_transcode"] = False
                    play_data = json.dumps(play_info)

                    home_window = HomeWindow()
                    home_window.setProperty("item_id", next_item_id)
                    home_window.setProperty("play_item_message", play_data)

                break


def stopAll(played_information):
    if len(played_information) == 0:
        return

    log.info("played_information : " + str(played_information))

    for item_url in played_information:
        data = played_information.get(item_url)
        if data is not None:
            log.info("item_url  : " + item_url)
            log.info("item_data : " + str(data))

            current_possition = data.get("currentPossition", 0)
            emby_item_id = data.get("item_id")

            if hasData(emby_item_id):
                log.info("Playback Stopped at: " + str(int(current_possition * 10000000)))

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
        log.info("Starting monitor service: " + str(args))
        self.played_information = {}

    @log_error()
    def onPlayBackStarted(self):
        # Will be called when xbmc starts playing a file
        stopAll(self.played_information)

        current_playing_file = xbmc.Player().getPlayingFile()
        log.info("onPlayBackStarted: " + current_playing_file)

        home_window = HomeWindow()
        emby_item_id = home_window.getProperty("item_id")
        playback_type = home_window.getProperty("PlaybackType_" + emby_item_id)

        # if we could not find the ID of the current item then return
        if emby_item_id is None or len(emby_item_id) == 0:
            return

        log.info("Sending Playback Started")
        postdata = {
            'QueueableMediaTypes': "Video",
            'CanSeek': True,
            'ItemId': emby_item_id,
            'MediaSourceId': emby_item_id,
            'PlayMethod': playback_type
        }

        log.debug("Sending POST play started: %s." % postdata)

        url = "{server}/emby/Sessions/Playing"
        download_utils.downloadUrl(url, postBody=postdata, method="POST")

        data = {}
        data["item_id"] = emby_item_id
        data["paused"] = False
        data["playback_type"] = playback_type
        self.played_information[current_playing_file] = data

        log.info("ADDING_FILE : " + current_playing_file)
        log.info("ADDING_FILE : " + str(self.played_information))

    @log_error()
    def onPlayBackEnded(self):
        # Will be called when kodi stops playing a file
        log.info("EmbyCon Service -> onPlayBackEnded")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    @log_error()
    def onPlayBackStopped(self):
        # Will be called when user stops kodi playing a file
        log.info("onPlayBackStopped")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    @log_error()
    def onPlayBackPaused(self):
        # Will be called when kodi pauses the video
        log.info("onPlayBackPaused")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = True
            sendProgress()

    @log_error()
    def onPlayBackResumed(self):
        # Will be called when kodi resumes the video
        log.info("onPlayBackResumed")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = False
            sendProgress()

    @log_error()
    def onPlayBackSeek(self, time, seekOffset):
        # Will be called when kodi seeks in video
        log.info("onPlayBackSeek")
        sendProgress()


monitor = Service()
last_progress_update = time.time()
lastMetricPing = time.time()
lastStartCheck = time.time()
startSent = False

ga = GoogleAnalytics()
try:
    ga.sendEventData("Version", "OS", platform.platform())
    ga.sendEventData("Version", "Python", platform.python_version())
except Exception as error:
    log.error("Exception in sending client meta info: " + str(error))

try:
    while not xbmc.abortRequested:

        home_window = HomeWindow()

        try:
            if not startSent and (time.time() - lastStartCheck) > 30:
                lastStartCheck = time.time()
                server_id = getServerId()
                if server_id is not None:
                    startSent = True
                    ga = GoogleAnalytics()
                    ga.sendEventData("Application", "Startup", server_id)

        except Exception as error:
            log.error("Exception in sending start message: " + str(error))
            raise

        if xbmc.Player().isPlaying():

            try:
                if (time.time() - lastMetricPing) > 300:
                    lastMetricPing = time.time()
                    ga = GoogleAnalytics()
                    ga.sendEventData("PlayAction", "PlayPing")
            except Exception, e:
                log.error("Exception in sending play ping: " + str(e))

            try:
                if (time.time() - last_progress_update) > 10:
                    last_progress_update = time.time()
                    sendProgress()

            except Exception as error:
                log.error("Exception in Playback Monitor : " + str(error))

        else:
            play_data = home_window.getProperty("play_item_message")
            if play_data:
                home_window.clearProperty("play_item_message")
                play_info = json.loads(play_data)
                playFile(play_info)

        xbmc.sleep(1000)
        HomeWindow().setProperty("Service_Timestamp", str(int(time.time())))

except Exception as error:
    ga = GoogleAnalytics()
    err_strings = ga.formatException()
    ga.sendEventData("Exception", err_strings[0], err_strings[1])
    log.error(str(error))
    log.error(str(err_strings))
    raise

# clear user and token when loggin off
home_window = HomeWindow()
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log.info("Service shutting down")
