from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import os
import threading

import xbmc
import xbmcaddon

from .lazylogger import LazyLogger
from .dialogs import PlayNextDialog
from .utils import translate_path

log = LazyLogger(__name__)


class PlayNextService(threading.Thread):

    stop_thread = False
    monitor = None

    def __init__(self, play_monitor):
        super(PlayNextService, self).__init__()
        self.monitor = play_monitor

    def run(self):

        from .play_utils import get_playing_data
        settings = xbmcaddon.Addon()
        play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))

        play_next_dialog = None
        play_next_triggered = False
        is_playing = False

        now_playing = None

        while not xbmc.Monitor().abortRequested() and not self.stop_thread:

            player = xbmc.Player()
            if player.isPlaying():

                if not is_playing:
                    settings = xbmcaddon.Addon()
                    play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))
                    log.debug("New play_next_trigger_time value: {0}".format(play_next_trigger_time))

                now_playing_file = player.getPlayingFile()
                if now_playing_file != now_playing:
                    # If the playing file has changed, reset the play next values
                    play_next_dialog = None
                    play_next_triggered = False
                    now_playing = now_playing_file

                duration = player.getTotalTime()
                position = player.getTime()
                trigger_time = play_next_trigger_time  # 300
                time_to_end = (duration - position)

                if not play_next_triggered and (trigger_time > time_to_end) and play_next_dialog is None:
                    play_next_triggered = True
                    log.debug("play_next_triggered hit at {0} seconds from end".format(time_to_end))

                    play_data = get_playing_data()
                    log.debug("play_next_triggered play_data : {0}".format(play_data))

                    next_episode = play_data.get("next_episode")
                    item_type = play_data.get("item_type")

                    if next_episode is not None and item_type == "Episode":

                        settings = xbmcaddon.Addon()
                        plugin_path = settings.getAddonInfo('path')
                        plugin_path_real = translate_path(os.path.join(plugin_path))

                        play_next_dialog = PlayNextDialog("PlayNextDialog.xml", plugin_path_real, "default", "720p")
                        play_next_dialog.set_episode_info(next_episode)
                        if play_next_dialog is not None:
                            play_next_dialog.show()

                is_playing = True

            else:
                play_next_triggered = False
                if play_next_dialog is not None:
                    play_next_dialog.close()
                    del play_next_dialog
                    play_next_dialog = None

                is_playing = False
                now_playing = None

            if xbmc.Monitor().waitForAbort(1):
                break

    def stop_service(self):
        log.debug("PlayNextService Stop Called")
        self.stop_thread = True
