from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import xbmcgui
import xbmc


from .lazylogger import LazyLogger
from .utils import seconds_to_ticks, ticks_to_seconds, translate_string, send_event_notification

log = LazyLogger(__name__)


class BitrateDialog(xbmcgui.WindowXMLDialog):

    slider_control = None
    bitrate_label = None
    initial_bitrate_value = 500
    max_bitrate_value = 15000
    min_bitrate_value = 500
    step_size = 100
    selected_transcode_value = 0

    def __init__(self, *args, **kwargs):
        log.debug("BitrateDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("ActionMenu: onInit")
        log.debug("ActionMenu: max: {} - min: {}, init: {}".format(self.max_bitrate_value, self.min_bitrate_value, self.initial_bitrate_value))
        self.action_exitkeys_id = [10, 13]

        self.slider_control = self.getControl(3000)
        self.slider_control.setInt(self.initial_bitrate_value, self.min_bitrate_value, self.step_size, self.max_bitrate_value)

        self.bitrate_label = self.getControl(3030)
        bitrate_label_string = str(self.slider_control.getInt()) + " Kbs"
        self.bitrate_label.setLabel(bitrate_label_string)
        self.getControl(3011).setLabel(translate_string(30314))

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("ActionMenu: onMessage: {0}".format(message))

    def onAction(self, action):

        bitrate_label_string = str(self.slider_control.getInt()) + " Kbs"
        self.bitrate_label.setLabel(bitrate_label_string)

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        elif action.getId() == 7:  # ENTER
            self.selected_transcode_value = self.slider_control.getInt()
            self.close()

    def onClick(self, control_id):
        if control_id == 3000:
            log.debug("ActionMenu: Selected Item: {0}".format(control_id))


class ResumeDialog(xbmcgui.WindowXMLDialog):
    resumePlay = -1
    resumeTimeStamp = ""
    action_exitkeys_id = None

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        log.debug("ResumeDialog INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        self.getControl(3010).setLabel(self.resumeTimeStamp)
        self.getControl(3011).setLabel(translate_string(30237))

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onClick(self, controlID):

        if controlID == 3010:
            self.resumePlay = 0
            self.close()
        if controlID == 3011:
            self.resumePlay = 1
            self.close()

    def setResumeTime(self, timeStamp):
        self.resumeTimeStamp = timeStamp

    def getResumeAction(self):
        return self.resumePlay


class SafeDeleteDialog(xbmcgui.WindowXMLDialog):

    confirm = False
    message = "Demo Message"
    heading = "Demo Heading"
    action_exitkeys_id = None

    def __init__(self, *args, **kwargs):
        log.debug("SafeDeleteDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("SafeDeleteDialog: onInit")
        self.action_exitkeys_id = [10, 13]

        message_control = self.getControl(3)
        message_control.setText(self.message)

        message_control = self.getControl(4)
        message_control.setLabel(self.heading)

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onMessage(self, message):
        log.debug("SafeDeleteDialog: onMessage: {0}".format(message))

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        else:
            log.debug("SafeDeleteDialog: onAction: {0}".format(action.getId()))

    def onClick(self, controlID):
        if controlID == 1:
            self.confirm = True
            self.close()
        elif controlID == 2:
            self.confirm = False
            self.close()


class PlayNextDialog(xbmcgui.WindowXMLDialog):

    action_exitkeys_id = None
    episode_info = None
    play_called = False

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
        log.debug("PlayNextDialog: onMessage: {0}".format(message))

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        else:
            log.debug("PlayNextDialog: onAction: {0}".format(action.getId()))

    def onClick(self, control_id):
        if control_id == 3013:
            log.debug("PlayNextDialog: Play Next Episode")
            self.play_called
            self.close()
            next_item_id = self.episode_info.get("Id")
            log.debug("Playing Next Episode: {0}".format(next_item_id))
            play_info = {}
            play_info["item_id"] = next_item_id
            play_info["auto_resume"] = "-1"
            play_info["force_transcode"] = False
            send_event_notification("jellycon_play_action", play_info)
        elif control_id == 3014:
            self.close()

    def set_episode_info(self, info):
        self.episode_info = info

    def get_play_called(self):
        return self.play_called

class SkipDialog(xbmcgui.WindowXMLDialog):

    action_exitkeys_id = None
    media_id = None
    start = None
    end = None
    
    has_been_dissmissed = False

    def __init__(self, *args, **kwargs):
        log.debug("SkipDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("SkipDialog: onInit")
        self.action_exitkeys_id = [10, 13]

    def onFocus(self, control_id):
        pass

    def doAction(self, action_id):
        pass

    def onMessage(self, message):
        log.debug("SkipDialog: onMessage: {0}".format(message))

    def onAction(self, action):
        log.debug("SkipDialog: onAction: {0}".format(action.getId()))
        if action.getId() == 10 or action.getId() == 92:  # ACTION_PREVIOUS_MENU & ACTION_NAV_BACK
            log.debug("SkipDialog: dismissing dialog so it does not open again")
            self.has_been_dissmissed = True
            self.close()

    def onClick(self, control_id):
        log.debug("SkipDialog: onClick: {0}".format(control_id))
        player = xbmc.Player()
        current_ticks = seconds_to_ticks(player.getTime())
        if self.start is not None and self.end is not None and current_ticks >= self.start and current_ticks <= self.end:
            log.debug("SkipDialog: skipping segment because current ticks ({0}) is in range".format(current_ticks))
            # If click during segment, skip it
            player.seekTime(ticks_to_seconds(self.end))
                                        
        self.close()

    def get_play_called(self):
        return self.play_called
    
    def is_button_shown(self):
        try:
            self.getFocus()
            return True
        except Exception:
            return False
