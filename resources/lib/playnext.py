import os
import threading

import xbmc
import xbmcgui
import xbmcaddon

from .simple_logging import SimpleLogging
from .play_utils import get_playing_data, send_event_notification

log = SimpleLogging(__name__)


class PlayNextService(threading.Thread):

    stop_thread = False
    monitor = None

    def __init__(self, play_monitor):
        super(PlayNextService, self).__init__()
        self.monitor = play_monitor

    def run(self):

        settings = xbmcaddon.Addon()
        play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))

        play_next_dialog = None
        play_next_triggered = False
        is_playing = False

        while not xbmc.Monitor().abortRequested() and not self.stop_thread:

            player = xbmc.Player()
            if player.isPlaying():

                if not is_playing:
                    settings = xbmcaddon.Addon()
                    play_next_trigger_time = int(settings.getSetting('play_next_trigger_time'))
                    log.debug("New play_next_trigger_time value: {0}", play_next_trigger_time)

                duration = player.getTotalTime()
                position = player.getTime()
                trigger_time = play_next_trigger_time  # 300
                time_to_end = (duration - position)

                if not play_next_triggered and (trigger_time > time_to_end) and play_next_dialog is None:
                    play_next_triggered = True
                    log.debug("play_next_triggered hit at {0} seconds from end", time_to_end)

                    play_data = get_playing_data(self.monitor.played_information)
                    log.debug("play_next_triggered play_data : {0}", play_data)

                    next_episode = play_data.get("next_episode")
                    item_type = play_data.get("item_type")

                    if next_episode is not None and item_type == "Episode":

                        settings = xbmcaddon.Addon()
                        plugin_path = settings.getAddonInfo('path')
                        plugin_path_real = xbmc.translatePath(os.path.join(plugin_path))

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

            if xbmc.Monitor().waitForAbort(1):
                break

    def stop_servcie(self):
        log.debug("PlayNextService Stop Called")
        self.stop_thread = True


class PlayNextDialog(xbmcgui.WindowXMLDialog):

    action_exitkeys_id = None
    episode_info = None

    def __init__(self, *args, **kwargs):
        log.debug("PlayNextDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("PlayNextDialog: onInit")
        self.action_exitkeys_id = [10, 13]

        index = self.episode_info.get("IndexNumber", -1)
        series_name = self.episode_info.get("SeriesName")
        next_epp_name = "Episode %02d - (%s)" % (index, self.episode_info.get("Name", "n/a"))

        series_label = self.getControl(3011)
        series_label.setLabel(series_name)

        series_label = self.getControl(3012)
        series_label.setLabel(next_epp_name)

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("PlayNextDialog: onMessage: {0}", message)

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        else:
            log.debug("PlayNextDialog: onAction: {0}", action.getId())

    def onClick(self, control_id):
        if control_id == 3013:
            log.debug("PlayNextDialog: Play Next Episode")
            self.close()
            next_item_id = self.episode_info.get("Id")
            log.debug("Playing Next Episode: {0}", next_item_id)
            play_info = {}
            play_info["item_id"] = next_item_id
            play_info["auto_resume"] = "-1"
            play_info["force_transcode"] = False
            send_event_notification("embycon_play_action", play_info)
        elif control_id == 3014:
            self.close()

    def set_episode_info(self, info):
        self.episode_info = info
