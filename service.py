# coding=utf-8
# Gnu General Public License - see LICENSE.TXT

import time
import json
import traceback
import binascii
from threading import Timer

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.downloadutils import DownloadUtils
from resources.lib.simple_logging import SimpleLogging
from resources.lib.play_utils import Service, PlaybackService, sendProgress
from resources.lib.kodi_utils import HomeWindow
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

# set up all the services
monitor = Service()
playback_service = PlaybackService(monitor)

home_window = HomeWindow()
last_progress_update = time.time()
last_content_check = time.time()
websocket_client = WebSocketClient()

# start the WebSocket Client running
settings = xbmcaddon.Addon(id='plugin.video.embycon')
remote_control = settings.getSetting('remoteControl') == "true"
if remote_control:
    websocket_client.start()


def get_now_playing():

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
                playerid) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount", "genre", "plotoutline", "uniqueid"] } }')
        result = unicode(result, 'utf-8', errors='ignore')
        log.debug("playing_item_details: {0}", result)

        result = json.loads(result)
        return result


def check_version():
    download_utils.checkVersion()


t = Timer(5.0, check_version)
t.start()

# monitor.abortRequested() is causes issues, it currently triggers for all addon cancelations which causes
# the service to exit when a user cancels an addon load action. This is a bug in Kodi.
# I am switching back to xbmc.abortRequested approach until kodi is fixed or I find a work arround

while not xbmc.abortRequested:

    try:
        if xbmc.Player().isPlaying():
            # if playing every 10 seconds updated the server with progress
            if (time.time() - last_progress_update) > 10:
                last_progress_update = time.time()
                sendProgress(monitor)
        else:
            # if not playing every 60 seonds check for new widget content
            if (time.time() - last_content_check) > 60:
                last_content_check = time.time()
                checkForNewContent()

        #get_now_playing()

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

log.debug("Service shutting down")
