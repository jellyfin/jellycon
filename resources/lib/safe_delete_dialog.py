# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui

from .simple_logging import SimpleLogging

log = SimpleLogging(__name__)


class SafeDeleteDialog(xbmcgui.WindowXMLDialog):

    confirm = False
    message = "Demo Message"
    heading = "Demo Heading"

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
        log.debug("SafeDeleteDialog: onMessage: {0}", message)

    def onAction(self, action):

        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()
        else:
            log.debug("SafeDeleteDialog: onAction: {0}", action.getId())

    def onClick(self, controlID):
        if controlID == 1:
            self.confirm = True
            self.close()
        elif controlID == 2:
            self.confirm = False
            self.close()
