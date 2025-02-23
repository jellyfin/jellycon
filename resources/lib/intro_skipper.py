from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import os
import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.play_utils import set_correct_skip_info
from resources.lib.utils import seconds_to_ticks, ticks_to_seconds, translate_path


from .lazylogger import LazyLogger
from .dialogs import SkipDialog


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
        
        while not xbmc.Monitor().abortRequested() and not self.stop_thread:
            player = xbmc.Player()
            if player.isPlaying():
                item_id = get_jellyfin_playing_item()
                if item_id is not None:
                    # Handle skip only on jellyfin items
                    current_ticks = seconds_to_ticks(player.getTime())

                    # Handle Intros
                    skip_intro_dialog = self.handle_intros(plugin_path_real, skip_intro_dialog, item_id, current_ticks, player)

                    # Handle Credits
                    skip_credit_dialog = self.handle_credits(plugin_path_real, skip_credit_dialog, item_id, current_ticks, player)

            else:
                if skip_intro_dialog is not None:
                    skip_intro_dialog.close()
                    skip_intro_dialog = None
                    
                if skip_credit_dialog is not None:
                    skip_credit_dialog.close()
                    skip_credit_dialog = None

            if xbmc.Monitor().waitForAbort(1):
                break
            
            xbmc.sleep(200)


    def handle_intros(self, plugin_path_real: str, skip_intro_dialog: SkipDialog, item_id: str, current_ticks: float, player: xbmc.Player):
        settings = xbmcaddon.Addon()
        intro_skip_action = settings.getSetting("intro_skipper_action")
        
        # In case do nothing is selected return
        if intro_skip_action == "2":
            return
        
        if skip_intro_dialog is None:
            skip_intro_dialog = SkipDialog("SkipDialog.xml", plugin_path_real, "default", "720p")
                        
        set_correct_skip_info(item_id, skip_intro_dialog)
                    
        is_intro = False
        if skip_intro_dialog.intro_start is not None and skip_intro_dialog.intro_end is not None:
            # Resets the dismiss var so that button can reappear in case of navigation in the timecodes
            if current_ticks < skip_intro_dialog.intro_start or current_ticks > skip_intro_dialog.intro_end:
                skip_intro_dialog.has_been_dissmissed = False
                        
            # Checks if segment is playing
            is_intro = current_ticks >= skip_intro_dialog.intro_start and current_ticks <= skip_intro_dialog.intro_end
            
            if intro_skip_action == "1" and is_intro:
                # If auto skip is enabled, skips to semgent ends automatically
                player.seekTime(ticks_to_seconds(skip_intro_dialog.intro_end))
                xbmcgui.Dialog().notification("JellyCon", "Intro Skipped")
            elif intro_skip_action == "0":
                # Otherwise show skip dialog
                if is_intro and not skip_intro_dialog.has_been_dissmissed:
                    skip_intro_dialog.show()
                else:
                    # Could not find doc on what happens when closing a closed dialog, but it seems fine
                    skip_intro_dialog.close()
                
        return skip_intro_dialog

    def handle_credits(self, plugin_path_real: str, skip_credit_dialog: SkipDialog, item_id: str, current_ticks: float, player: xbmc.Player):
        settings = xbmcaddon.Addon()
        credit_skip_action = settings.getSetting("credit_skipper_action")
        
        # In case do nothing is selected return

        if credit_skip_action == "2":
            return
        
        if skip_credit_dialog is None:
            skip_credit_dialog = SkipDialog("SkipDialog.xml", plugin_path_real, "default", "720p")
                    
        set_correct_skip_info(item_id, skip_credit_dialog)

        is_credit = False
        if skip_credit_dialog.credit_start is not None and skip_credit_dialog.credit_end is not None:
            # Resets the dismiss var so that button can reappear in case of navigation in the timecodes
            if current_ticks < skip_credit_dialog.credit_start or current_ticks > skip_credit_dialog.credit_end:
                skip_credit_dialog.has_been_dissmissed = False

            # Checks if segment is playing
            is_credit = current_ticks >= skip_credit_dialog.credit_start and current_ticks <= skip_credit_dialog.credit_end
            
            if credit_skip_action == "1" and is_credit:
                # If auto skip is enabled, skips to semgent ends automatically
                player.seekTime(ticks_to_seconds(skip_credit_dialog.credit_end))
                xbmcgui.Dialog().notification("JellyCon", "Credit Skipped")
            elif credit_skip_action == "0":
                # Otherwise show skip dialog
                if is_credit and not skip_credit_dialog.has_been_dissmissed:
                    skip_credit_dialog.show()
                else:
                    skip_credit_dialog.close()
                
        return skip_credit_dialog
    
    def stop_service(self):
        log.debug("IntroSkipperService Stop Called")
        self.stop_thread = True
