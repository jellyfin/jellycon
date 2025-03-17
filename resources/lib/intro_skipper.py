from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import os
import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.play_utils import get_media_segments
from resources.lib.utils import seconds_to_ticks, ticks_to_seconds, translate_path
from resources.lib.intro_skipper_utils import get_setting_skip_action, set_correct_skip_info


from .lazylogger import LazyLogger
from .dialogs import SkipDialog

from typing import Literal

log = LazyLogger(__name__)


class IntroSkipperService(threading.Thread):

    stop_thread = False
    monitor = None

    def __init__(self, play_monitor):
        super(IntroSkipperService, self).__init__()
        self.monitor = play_monitor

    def run(self):

        from .play_utils import get_jellyfin_playing_item
        settings = xbmcaddon.Addon()
        plugin_path = settings.getAddonInfo('path')
        plugin_path_real = translate_path(os.path.join(plugin_path))
        
        skip_intro_dialog = None
        skip_credit_dialog = None
        skip_commercial_dialog = None
        skip_preview_dialog = None
        skip_recap_dialog = None
        
        segments = None
        playing_item_id = None
        
        log.debug("SkipService: starting service")
        
        while not xbmc.Monitor().abortRequested() and not self.stop_thread:
            player = xbmc.Player()
            if player.isPlaying():
                item_id = get_jellyfin_playing_item()
                if item_id is not None:
                    log.debug("SkipService: playing item is from jellyfin : {0}".format(item_id))
                    
                    # If item id has changed or is new, retrieve segments
                    if playing_item_id is None or playing_item_id != item_id :
                        log.debug("SkipService: item is new, retrieving media segments : {0}".format(item_id))
                        segments = get_media_segments(item_id)
                        
                    # Setting global playing item to current playing item
                    playing_item_id = item_id
                    
                    # Handle skip only on jellyfin items
                    current_ticks = seconds_to_ticks(player.getTime())

                    # Handle Intros
                    skip_intro_dialog = self.handle_dialog(plugin_path_real, skip_intro_dialog, item_id, current_ticks, player, segments, "Intro")
                    # Handle Credits
                    skip_credit_dialog = self.handle_dialog(plugin_path_real, skip_credit_dialog, item_id, current_ticks, player, segments, "Outro")
                    # Handle commercial
                    skip_commercial_dialog = self.handle_dialog(plugin_path_real, skip_commercial_dialog, item_id, current_ticks, player, segments, "Commercial")
                    # Handle preview
                    skip_preview_dialog = self.handle_dialog(plugin_path_real, skip_preview_dialog, item_id, current_ticks, player, segments, "Preview")
                    # Handle recap
                    skip_recap_dialog = self.handle_dialog(plugin_path_real, skip_recap_dialog, item_id, current_ticks, player, segments, "Recap")

            else:
                playing_item_id = None
                if skip_intro_dialog is not None:
                    log.debug("SkipService: Playback stopped, killing Intro dialog")
                    skip_intro_dialog.close()
                    skip_intro_dialog = None
                    
                if skip_credit_dialog is not None:
                    log.debug("SkipService: Playback stopped, killing Outro dialog")
                    skip_credit_dialog.close()
                    skip_credit_dialog = None
                    
                if skip_commercial_dialog is not None:
                    log.debug("SkipService: Playback stopped, killing Commercial dialog")
                    skip_commercial_dialog.close()
                    skip_commercial_dialog = None
                    
                if skip_preview_dialog is not None:
                    log.debug("SkipService: Playback stopped, killing Preview dialog")
                    skip_preview_dialog.close()
                    skip_preview_dialog = None
                    
                if skip_recap_dialog is not None:
                    log.debug("SkipService: Playback stopped, killing Recap dialog")
                    skip_recap_dialog.close()
                    skip_recap_dialog = None

            if xbmc.Monitor().waitForAbort(1):
                break
            
            xbmc.sleep(200)

    
    def handle_dialog(self, plugin_path_real: str, dialog: SkipDialog, item_id: str, current_ticks: float, player: xbmc.Player, segments, type: Literal["Commercial", "Preview", "Recap", "Outro", "Intro"]):
        skip_action = get_setting_skip_action(type)
        
        # In case do nothing is selected return
        if skip_action == "2":
            log.debug("SkipService: ignore {0} is selected".format(type))
            return None
        
        if dialog is None:
            log.debug("SkipService: init dialog")
            dialog = SkipDialog("SkipDialog.xml", plugin_path_real, "default", "720p")
                        
        set_correct_skip_info(item_id, dialog, segments, type)
                    
        is_segment = False
        if dialog.start is not None and dialog.end is not None:
            # Resets the dismiss var so that button can reappear in case of navigation in the timecodes
            if (current_ticks < dialog.start or current_ticks > dialog.end) and dialog.has_been_dissmissed is True:
                log.debug("SkipService: {0} skip was dismissed. It is reseted beacause timecode is outised of segment")
                dialog.has_been_dissmissed = False
                        
            # Checks if segment is playing
            is_segment = current_ticks >= dialog.start and current_ticks <= dialog.end
            
            if skip_action == "1" and is_segment:
                log.debug("SkipService: {0} is set to automatic skip, skipping segment".format(type))
                # If auto skip is enabled, skips to semgent ends automatically
                player.seekTime(ticks_to_seconds(dialog.end))
                xbmcgui.Dialog().notification("JellyCon", "{0} Skipped".format(type))
            elif skip_action == "0":
                # Otherwise show skip dialog
                if is_segment and not dialog.has_been_dissmissed:
                    log.debug("SkipService: {0} is playing, showing dialog".format(type))
                    dialog.show()
                else:
                    # Could not find doc on what happens when closing a closed dialog, but it seems fine
                    log.debug("SkipService: {0} is not playing, closing dialog".format(type))
                    dialog.close()
                
        return dialog
    

    def stop_service(self):
        log.debug("IntroSkipperService Stop Called")
        self.stop_thread = True
