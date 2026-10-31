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
from .utils import load_user_details

log = LazyLogger(__name__)

# Jellyfin replies to JSON KeepAlive messages; require replies to detect a
# stale connection.
KEEPALIVE_INTERVAL = 30
KEEPALIVE_CHECK = 10
KEEPALIVE_TIMEOUT = 45


class WebSocketClient(threading.Thread):

    def __init__(self, library_change_monitor):

        threading.Thread.__init__(self)

        self._client = None
        self._stop_websocket = False
        self._library_monitor = library_change_monitor
        self.monitor = xbmc.Monitor()

        self.websocket_error = False
        self.last_keepalive_response = time.time()
        self._watchdog_timer = None
        self._keepalive_timer = None
        # Guards the check-and-reschedule of the timers so a timer thread
        # cannot slip a new pending timer in behind stop_client().
        self._timer_lock = threading.RLock()
        settings = xbmcaddon.Addon()
        user_details = load_user_details()

        self.api = API(
            settings.getSetting('server_address'),
            user_details.get('user_id'),
            user_details.get('token')
        )

    def on_message(self, ws, message):

        result = json.loads(message)
        message_type = result['MessageType']

        if message_type == "KeepAlive":
            self.last_keepalive_response = time.time()
            return

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
        self.last_keepalive_response = time.time()
        self.api.post_capabilities()
        # Cancel and reschedule as one atomic step, otherwise stop_client()
        # could land in between and leave a watchdog pending at shutdown.
        with self._timer_lock:
            self._cancel_timers()
            if self._stop_websocket:
                return
            self.schedule_keepalive_watchdog(ws)
        # Outside the lock: ws.send() may block, and stop_client() should
        # not have to wait for it.
        self.send_keepalive(ws)

    def on_error(self, ws, error):
        self.websocket_error = True
        log.debug("Error: {0}".format(error))

    def run(self):

        while self.api.token is None or self.api.token == "":
            if self.monitor.waitForAbort(11):
                return

        # Get the appropriate prefix for the websocket
        settings = xbmcaddon.Addon()
        server = settings.getSetting('server_address')
        if "https://" in server:
            server = server.replace('https://', 'wss://')
        else:
            server = server.replace('http://', 'ws://')

        websocket_url = "{}/socket".format(server)
        log.debug("websocket url: {0}".format(websocket_url))

        log.debug("Starting WebSocketClient")

        while not self.monitor.abortRequested():

            self.websocket_error = False
            self._cancel_timers()

            headers = self.api.headers
            self._client = websocket.WebSocketApp(
                websocket_url,
                header=headers,
                on_open=lambda ws: self.on_open(ws),
                on_message=lambda ws, message: self.on_message(ws, message),
                on_error=lambda ws, error: self.on_error(ws, error))

            try:
                self._client.run_forever()
            except Exception as error:
                log.error("WebSocket loop failed: {0}".format(error))

            if self._stop_websocket:
                break

            if self.monitor.waitForAbort(20):
                # Abort was requested, exit
                break

            log.debug("Reconnecting WebSocket")

        log.debug("WebSocketClient Stopped")

    def stop_client(self):

        with self._timer_lock:
            self._stop_websocket = True
            self._cancel_timers()
        if self._client is not None:
            self._client.close()
        log.debug("Stopping WebSocket (stop_client called)")

    def send_keepalive(self, ws):
        # Stop the keepalive cycle if an error has been detected
        with self._timer_lock:
            if (self._stop_websocket or self.websocket_error or
                    ws is not self._client):
                return
        keepalive_payload = json.dumps({
            "MessageType": "KeepAlive",
            "Data": KEEPALIVE_INTERVAL
        })
        # Send the keepalive, or register an error
        try:
            ws.send(keepalive_payload)
        except Exception as error:
            self.websocket_error = True
            log.error("WebSocket keepalive failed: {0}".format(error))
            try:
                ws.close()
            except Exception:
                pass
            return
        # Schedule the next message. Re-check under the lock: stop_client()
        # may have run while we were sending, and Timer.cancel() is a no-op
        # once the thread has started, so scheduling now would leave a
        # pending non-daemon thread blocking interpreter teardown.
        with self._timer_lock:
            if self._stop_websocket:
                return
            self.schedule_keepalive(ws)

    def schedule_keepalive(self, ws):
        # Schedule a keepalive message in 30 seconds. Cancel any pending
        # timer first: overwriting the reference would orphan it, leaving an
        # unreachable non-daemon thread that blocks interpreter teardown.
        with self._timer_lock:
            if self._keepalive_timer is not None:
                self._keepalive_timer.cancel()
            timer = threading.Timer(
                KEEPALIVE_INTERVAL, self.send_keepalive, kwargs={'ws': ws})
            self._keepalive_timer = timer
            timer.start()

    def _cancel_timers(self):
        with self._timer_lock:
            if self._watchdog_timer:
                self._watchdog_timer.cancel()
                self._watchdog_timer = None
            if self._keepalive_timer:
                self._keepalive_timer.cancel()
                self._keepalive_timer = None

    def schedule_keepalive_watchdog(self, ws):
        # Check the server's application-level KeepAlive response.
        with self._timer_lock:
            if self._watchdog_timer is not None:
                self._watchdog_timer.cancel()
            timer = threading.Timer(
                KEEPALIVE_CHECK,
                self.check_keepalive_watchdog,
                kwargs={'ws': ws})
            self._watchdog_timer = timer
            timer.start()

    def check_keepalive_watchdog(self, ws):
        # Stop stale timers from previous connections / after shutdown
        with self._timer_lock:
            if self._stop_websocket or ws is not self._client:
                return
        elapsed = time.time() - self.last_keepalive_response
        if elapsed > KEEPALIVE_TIMEOUT:
            log.debug(
                "No KeepAlive response for {0:.0f}s, reconnecting".format(
                    elapsed))
            try:
                ws.close()
            except Exception:
                pass
            return
        # Re-check under the lock so we cannot reschedule past stop_client().
        with self._timer_lock:
            if self._stop_websocket or ws is not self._client:
                return
            self.schedule_keepalive_watchdog(ws)
