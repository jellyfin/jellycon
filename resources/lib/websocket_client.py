from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import json
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui
import websocket

from .jellyfin import API
from .functions import play_action
from .lazylogger import LazyLogger
from .jsonrpc import JsonRpc
from .kodi_utils import HomeWindow
from .utils import get_device_id, load_user_details

log = LazyLogger(__name__)


class WebSocketClient(threading.Thread):

    _shared_state = {}

    _client = None
    _stop_websocket = False
    _library_monitor = None

    def __init__(self, library_change_monitor):

        self.__dict__ = self._shared_state
        self.monitor = xbmc.Monitor()
        self.retry_count = 0

        self.device_id = get_device_id()

        self._library_monitor = library_change_monitor

        threading.Thread.__init__(self)

    def on_message(self, ws, message):

        result = json.loads(message)
        message_type = result['MessageType']

        if message_type == 'Play':
            data = result['Data']
            self._play(data)

        elif message_type == 'Playstate':
            data = result['Data']
            self._playstate(data)

        elif message_type == "UserDataChanged":
            data = result['Data']
            self._library_changed(data)

        elif message_type == "LibraryChanged":
            data = result['Data']
            self._library_changed(data)

        elif message_type == "GeneralCommand":
            data = result['Data']
            self._general_commands(data)

        else:
            log.debug("WebSocket Message Type: {0}".format(message))

    def _library_changed(self, data):
        log.debug("Library_Changed: {0}".format(data))
        self._library_monitor.check_for_updates()

    def _play(self, data):

        item_ids = data['ItemIds']
        command = data['PlayCommand']

        if command == 'PlayNow':
            home_screen = HomeWindow()
            home_screen.set_property("skip_select_user", "true")

            startat = data.get('StartPositionTicks', -1)
            log.debug("WebSocket Message PlayNow: {0}".format(data))

            media_source_id = data.get("MediaSourceId", "")
            subtitle_stream_index = data.get("SubtitleStreamIndex", None)
            audio_stream_index = data.get("AudioStreamIndex", None)

            start_index = data.get("StartIndex", 0)

            if start_index > 0 and start_index < len(item_ids):
                item_ids = item_ids[start_index:]

            if len(item_ids) == 1:
                item_ids = item_ids[0]

            params = {}
            params["item_id"] = item_ids
            params["auto_resume"] = str(startat)
            params["media_source_id"] = media_source_id
            params["subtitle_stream_index"] = subtitle_stream_index
            params["audio_stream_index"] = audio_stream_index
            play_action(params)

    def _playstate(self, data):

        command = data['Command']
        player = xbmc.Player()

        actions = {

            'Stop': player.stop,
            'Unpause': player.pause,
            'Pause': player.pause,
            'PlayPause': player.pause,
            'NextTrack': player.playnext,
            'PreviousTrack': player.playprevious
        }
        if command == 'Seek':

            if player.isPlaying():
                seek_to = data['SeekPositionTicks']
                seek_time = seek_to / 10000000.0
                player.seekTime(seek_time)
                log.debug("Seek to {0}".format(seek_time))

        elif command in actions:
            actions[command]()
            log.debug("Command: {0} completed".format(command))

        else:
            log.debug("Unknown command: {0}".format(command))
            return

    def _general_commands(self, data):

        command = data['Name']
        arguments = data['Arguments']

        if command in ('Mute',
                       'Unmute',
                       'SetVolume',
                       'SetSubtitleStreamIndex',
                       'SetAudioStreamIndex',
                       'SetRepeatMode'):

            player = xbmc.Player()
            # These commands need to be reported back
            if command == 'Mute':
                xbmc.executebuiltin('Mute')

            elif command == 'Unmute':
                xbmc.executebuiltin('Mute')

            elif command == 'SetVolume':
                volume = arguments['Volume']
                xbmc.executebuiltin(
                    'SetVolume({}[,showvolumebar])'.format(volume)
                )

            elif command == 'SetAudioStreamIndex':
                index = int(arguments['Index'])
                player.setAudioStream(index - 1)

            elif command == 'SetSubtitleStreamIndex':
                index = int(arguments['Index'])
                player.setSubtitleStream(index - 1)

            elif command == 'SetRepeatMode':
                mode = arguments['RepeatMode']
                xbmc.executebuiltin('xbmc.PlayerControl({})'.format(mode))

        elif command == 'DisplayMessage':

            # header = arguments['Header']
            text = arguments['Text']
            # show notification here
            log.debug("WebSocket DisplayMessage: {0}".format(text))
            xbmcgui.Dialog().notification("JellyCon", text)

        elif command == 'SendString':

            params = {

                'text': arguments['String'],
                'done': False
            }
            JsonRpc('Input.SendText').execute(params)

        elif command in ('MoveUp', 'MoveDown', 'MoveRight', 'MoveLeft'):
            # Commands that should wake up display
            actions = {

                'MoveUp': "Input.Up",
                'MoveDown': "Input.Down",
                'MoveRight': "Input.Right",
                'MoveLeft': "Input.Left"
            }
            JsonRpc(actions[command]).execute()

        elif command == 'GoHome':
            JsonRpc('GUI.ActivateWindow').execute({'window': "home"})

        elif command == "Guide":
            JsonRpc('GUI.ActivateWindow').execute({'window': "tvguide"})

        else:
            builtin = {

                'ToggleFullscreen': 'Action(FullScreen)',
                'ToggleOsdMenu': 'Action(OSD)',
                'ToggleContextMenu': 'Action(ContextMenu)',
                'Select': 'Action(Select)',
                'Back': 'Action(back)',
                'PageUp': 'Action(PageUp)',
                'NextLetter': 'Action(NextLetter)',
                'GoToSearch': 'VideoLibrary.Search',
                'GoToSettings': 'ActivateWindow(Settings)',
                'PageDown': 'Action(PageDown)',
                'PreviousLetter': 'Action(PrevLetter)',
                'TakeScreenshot': 'TakeScreenshot',
                'ToggleMute': 'Mute',
                'VolumeUp': 'Action(VolumeUp)',
                'VolumeDown': 'Action(VolumeDown)',
            }
            if command in builtin:
                xbmc.executebuiltin(builtin[command])

    def on_open(self, ws):
        log.debug("Connected")
        self.retry_count = 0
        self.post_capabilities()

    def on_error(self, ws, error):
        log.debug("Error: {0}".format(error))

    def run(self):

        token = None
        while token is None or token == "":
            user_details = load_user_details()
            token = user_details.get('token')
            if self.monitor.waitForAbort(10):
                return

        # Get the appropriate prefix for the websocket
        settings = xbmcaddon.Addon()
        server = settings.getSetting('server_address')
        if "https://" in server:
            server = server.replace('https://', 'wss://')
        else:
            server = server.replace('http://', 'ws://')

        websocket_url = "{}/socket?api_key={}&deviceId={}".format(
            server, token, self.device_id
        )
        log.debug("websocket url: {0}".format(websocket_url))

        self._client = websocket.WebSocketApp(
            websocket_url,
            on_open=lambda ws: self.on_open(ws),
            on_message=lambda ws, message: self.on_message(ws, message),
            on_error=lambda ws, error: self.on_error(ws, error))

        log.debug("Starting WebSocketClient")

        while not self.monitor.abortRequested():

            time.sleep(self.retry_count * 5)
            self._client.run_forever(ping_interval=10)

            if self._stop_websocket:
                break

            if self.monitor.waitForAbort(20):
                # Abort was requested, exit
                break

            if self.retry_count < 12:
                self.retry_count += 1
            log.debug("Reconnecting WebSocket")

        log.debug("WebSocketClient Stopped")

    def stop_client(self):

        self._stop_websocket = True
        if self._client is not None:
            self._client.close()
        log.debug("Stopping WebSocket (stop_client called)")

    def post_capabilities(self):

        settings = xbmcaddon.Addon()
        user_details = load_user_details()

        api = API(
            settings.getSetting('server_address'),
            user_details.get('user_id'),
            user_details.get('token')
        )

        api.post_capabilities()
