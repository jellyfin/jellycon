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
from resources.lib.widgets import checkForNewContent, set_background_image
from resources.lib.websocket_client import WebSocketClient
from resources.lib.menu_functions import set_library_window_values

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
last_background_update = 0
websocket_client = WebSocketClient()

# session id
# TODO: this is used to append to the end of PLAY urls, this is to stop mark watched from overriding the Emby ones
home_window.setProperty("session_id", str(time.time()))

# start the WebSocket Client running
settings = xbmcaddon.Addon(id='plugin.video.embycon')
remote_control = settings.getSetting('remoteControl') == "true"
if remote_control:
    websocket_client.start()

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
            if (time.time() - last_content_check) > 60:
                last_content_check = time.time()
                checkForNewContent()
            if (time.time() - last_background_update) > 30:
                last_background_update = time.time()
                set_library_window_values()
                set_background_image()

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
