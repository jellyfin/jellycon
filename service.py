# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcaddon
import time
from datetime import datetime

from resources.lib.downloadutils import DownloadUtils
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import playFile
from resources.lib.kodi_utils import HomeWindow

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

    settings = xbmcaddon.Addon(id='plugin.video.embycon')
    port = settings.getSetting('port')
    host = settings.getSetting('ipaddress')
    server = host + ":" + port

    url = "http://" + server + "/emby/Sessions/Playing/Progress"
    download_utils.downloadUrl(url, postBody=postdata, method="POST")


def stopAll(played_information):
    if len(played_information) == 0:
        return

    log.info("played_information : " + str(played_information))

    for item_url in played_information:
        data = played_information.get(item_url)
        if data is not None:
            log.info("item_url  : " + item_url)
            log.info("item_data : " + str(data))

            current_possition = data.get("currentPossition")
            emby_item_id = data.get("item_id")

            if hasData(emby_item_id):
                log.info("Playback Stopped at: " + str(int(current_possition * 10000000)))

                settings = xbmcaddon.Addon(id='plugin.video.embycon')
                port = settings.getSetting('port')
                host = settings.getSetting('ipaddress')
                server = host + ":" + port

                url = "http://" + server + "/emby/Sessions/Playing/Stopped"
                postdata = {
                    'ItemId': emby_item_id,
                    'MediaSourceId': emby_item_id,
                    'PositionTicks': int(current_possition * 10000000)
                }
                download_utils.downloadUrl(url, postBody=postdata, method="POST")

    played_information.clear()


class Service(xbmc.Player):
    played_information = {}

    def __init__(self, *args):
        log.info("Starting monitor service: " + str(args))
        self.played_information = {}
        pass

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

        settings = xbmcaddon.Addon(id='plugin.video.embycon')
        port = settings.getSetting('port')
        host = settings.getSetting('ipaddress')
        server = host + ":" + port

        url = "http://" + server + "/emby/Sessions/Playing"
        download_utils.downloadUrl(url, postBody=postdata, method="POST")

        data = {}
        data["item_id"] = emby_item_id
        data["paused"] = False
        data["playback_type"] = playback_type
        self.played_information[current_playing_file] = data

        log.info("ADDING_FILE : " + current_playing_file)
        log.info("ADDING_FILE : " + str(self.played_information))

    def onPlayBackEnded(self):
        # Will be called when kodi stops playing a file
        log.info("EmbyCon Service -> onPlayBackEnded")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    def onPlayBackStopped(self):
        # Will be called when user stops kodi playing a file
        log.info("onPlayBackStopped")
        home_window = HomeWindow()
        home_window.clearProperty("item_id")
        stopAll(self.played_information)

    def onPlayBackPaused(self):
        # Will be called when kodi pauses the video
        log.info("onPlayBackPaused")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = True
            sendProgress()

    def onPlayBackResumed(self):
        # Will be called when kodi resumes the video
        log.info("onPlayBackResumed")
        current_file = xbmc.Player().getPlayingFile()
        play_data = monitor.played_information.get(current_file)

        if play_data is not None:
            play_data['paused'] = False
            sendProgress()

    def onPlayBackSeek(self, time, seekOffset):
        # Will be called when kodi seeks in video
        log.info("onPlayBackSeek")
        sendProgress()


monitor = Service()
last_progress_update = datetime.today()

while not xbmc.abortRequested:

    home_window = HomeWindow()

    if xbmc.Player().isPlaying():
        try:
            # send update
            td = datetime.today() - last_progress_update
            sec_diff = td.seconds
            if sec_diff > 10:
                sendProgress()
                last_progress_update = datetime.today()

        except Exception, e:
            log.error("Exception in Playback Monitor : " + str(e))
            pass

    else:
        emby_item_id = home_window.getProperty("play_item_id")
        emby_item_resume = home_window.getProperty("play_item_resume")
        if emby_item_id and emby_item_resume:
            home_window.clearProperty("play_item_id")
            home_window.clearProperty("play_item_resume")
            playFile(emby_item_id, emby_item_resume)

    xbmc.sleep(1000)
    HomeWindow().setProperty("Service_Timestamp", str(int(time.time())))

# clear user and token when loggin off
home_window = HomeWindow()
home_window.clearProperty("userid")
home_window.clearProperty("AccessToken")
home_window.clearProperty("Params")

log.info("Service shutting down")
