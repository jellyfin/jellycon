# -*- coding: utf-8 -*-

#################################################################################################

import json
import threading
import websocket

import xbmc
import xbmcgui

from functions import PLAY
from simple_logging import SimpleLogging
import clientinfo
import downloadutils
from json_rpc import json_rpc

log = SimpleLogging(__name__)

class WebSocketClient(threading.Thread):

    _shared_state = {}

    _client = None
    _stop_websocket = False

    def __init__(self):

        self.__dict__ = self._shared_state
        self.monitor = xbmc.Monitor()

        self.client_info = clientinfo.ClientInformation()
        self.device_id = self.client_info.getDeviceId()

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
            log.debug("WebSocket Message UserDataChanged: {0}", message)

        elif message_type == "LibraryChanged":
            log.debug("WebSocket Message LibraryChanged: {0}", message)

        elif message_type == "GeneralCommand":
            data = result['Data']
            self._general_commands(data)

        else:
            log.debug("WebSocket Message Type: {0}", message)

    def _play(cls, data):

        item_ids = data['ItemIds']
        command = data['PlayCommand']

        if command == 'PlayNow':
            startat = data.get('StartPositionTicks', 0)
            log.debug("WebSocket Message PlayNow: {0}", data)

            media_source_id = data.get("MediaSourceId", "")

            if len(item_ids) == 1:
                item_ids = item_ids[0]

            params = {}
            params["item_id"] = item_ids
            params["auto_resume"] = str(startat)
            params["media_source_id"] = media_source_id
            params["use_default"] = "true"
            PLAY(params)


    def _playstate(cls, data):

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
                log.debug("Seek to {0}", seek_time)

        elif command in actions:
            actions[command]()
            log.debug("Command: {0} completed",  command)

        else:
            log.debug("Unknown command: {0}", command)
            return

    def _general_commands(cls, data):

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
                xbmc.executebuiltin('SetVolume(%s[,showvolumebar])' % volume)

            elif command == 'SetAudioStreamIndex':
                index = int(arguments['Index'])
                player.setAudioStream(index - 1)

            elif command == 'SetRepeatMode':
                mode = arguments['RepeatMode']
                xbmc.executebuiltin('xbmc.PlayerControl(%s)' % mode)

        elif command == 'DisplayMessage':

            header = arguments['Header']
            text = arguments['Text']
            # show notification here
            log.debug("WebSocket DisplayMessage: {0}", text)
            xbmcgui.Dialog().notification("EmbyCon", text)

        elif command == 'SendString':

            params = {

                'text': arguments['String'],
                'done': False
            }
            json_rpc('Input.SendText').execute(params)

        elif command in ('MoveUp', 'MoveDown', 'MoveRight', 'MoveLeft'):
            # Commands that should wake up display
            actions = {

                'MoveUp': "Input.Up",
                'MoveDown': "Input.Down",
                'MoveRight': "Input.Right",
                'MoveLeft': "Input.Left"
            }
            json_rpc(actions[command]).execute()

        elif command == 'GoHome':
            json_rpc('GUI.ActivateWindow').execute({'window': "home"})

        elif command == "Guide":
            json_rpc('GUI.ActivateWindow').execute({'window': "tvguide"})

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

    def on_close(self, ws):
        log.debug("closed")

    def on_open(self, ws):
        self.post_capabilities()

    def on_error(self, ws, error):
        log.debug("Error: {0}", error)

    def run(self):

        # websocket.enableTrace(True)
        download_utils = downloadutils.DownloadUtils()

        token = None
        while token is None or token == "":
            token = download_utils.authenticate()
            if self.monitor.waitForAbort(10):
                return

        # Get the appropriate prefix for the websocket
        server = download_utils.getServer()
        if "https" in server:
            server = server.replace('https', "wss")
        else:
            server = server.replace('http', "ws")

        websocket_url = "%s/embywebsocket?api_key=%s&deviceId=%s" % (server, token, self.device_id)
        log.debug("websocket url: {0}", websocket_url)

        self._client = websocket.WebSocketApp(websocket_url,
                                              on_message=self.on_message,
                                              on_error=self.on_error,
                                              on_close=self.on_close)
        self._client.on_open = self.on_open
        log.debug("Starting WebSocketClient")

        while not self.monitor.abortRequested():

            self._client.run_forever(ping_interval=10)

            if self._stop_websocket:
                break

            if self.monitor.waitForAbort(20):
                # Abort was requested, exit
                break

            log.debug("Reconnecting WebSocket")

        log.debug("WebSocketClient Stopped")

    def stop_client(self):

        self._stop_websocket = True
        if self._client is not None:
            self._client.close()
        log.debug("Stopping WebSocket (stop_client called)")

    def post_capabilities(self):

        download_utils = downloadutils.DownloadUtils()
        download_utils.post_capabilities()


