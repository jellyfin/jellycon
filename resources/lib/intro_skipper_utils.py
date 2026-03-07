from typing import Literal

import xbmcaddon

from .lazylogger import LazyLogger
from .dialogs import SkipDialog

from .utils import seconds_to_ticks

log = LazyLogger(__name__)

def get_setting_skip_action(type: Literal["Commercial", "Preview", "Recap", "Outro", "Intro"]):
    settings = xbmcaddon.Addon()
    if (type == "Commercial"):
        return settings.getSetting("commercial_skipper_action")
    elif (type == "Preview"):
        return settings.getSetting("preview_skipper_action")
    elif (type == "Recap"):
        return settings.getSetting("recap_skipper_action")
    elif (type == "Outro"):
        return settings.getSetting("credit_skipper_action")
    elif (type == "Intro"):
        return settings.getSetting("intro_skipper_action")
    return ""

def get_setting_skip_start_offset(type: Literal["Commercial", "Preview", "Recap", "Outro", "Intro"]):
    settings = xbmcaddon.Addon()
    if (type == "Commercial"):
        return settings.getSettingInt("commercial_skipper_start_offset")
    elif (type == "Preview"):
        return settings.getSettingInt("preview_skipper_start_offset")
    elif (type == "Recap"):
        return settings.getSettingInt("recap_skipper_start_offset")
    elif (type == "Outro"):
        return settings.getSettingInt("credit_skipper_start_offset")
    elif (type == "Intro"):
        return settings.getSettingInt("intro_skipper_start_offset")
    return 0

def get_setting_skip_end_offset(type: Literal["Commercial", "Preview", "Recap", "Outro", "Intro"]):
    settings = xbmcaddon.Addon()
    if (type == "Commercial"):
        return settings.getSettingInt("commercial_skipper_end_offset")
    elif (type == "Preview"):
        return settings.getSettingInt("preview_skipper_end_offset")
    elif (type == "Recap"):
        return settings.getSettingInt("recap_skipper_end_offset")
    elif (type == "Outro"):
        return settings.getSettingInt("credit_skipper_end_offset")
    elif (type == "Intro"):
        return settings.getSettingInt("intro_skipper_end_offset")
    return 0

def set_correct_skip_info(item_id: str, skip_dialog: SkipDialog, segment: dict):
    if (skip_dialog.media_id is None or skip_dialog.media_id != item_id) and item_id is not None:
        # If playback item has changed (or is new), sets its id and set media segments info
        log.debug("SkipDialogInfo : Media Id has changed to {0}, setting segments".format(item_id))
        skip_dialog.media_id = item_id
        skip_dialog.has_been_dissmissed = False
        if segment is not None:
            # Find the intro and outro timings
            start = segment.get("StartTicks")
            end = segment.get("EndTicks")

            # Sets timings with offsets if defined in settings
            if start is not None:
                skip_dialog.start = start + seconds_to_ticks(get_setting_skip_start_offset(type))
                log.debug("SkipDialogInfo : Setting {0} start to {1}".format(type, skip_dialog.start))
            if end is not None:
                skip_dialog.end = end - seconds_to_ticks(get_setting_skip_end_offset(type))
                log.debug("SkipDialogInfo : Setting {0} end to {1}".format(type, skip_dialog.end))
