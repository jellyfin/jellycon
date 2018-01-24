import xbmc
import xbmcaddon
import xbmcgui

from simple_logging import SimpleLogging

log = SimpleLogging(__name__)

class ActionMenu(xbmcgui.WindowXMLDialog):

    selected_action = None
    action_items = None

    def __init__(self, *args, **kwargs):
        log.debug("ActionMenu: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("ActionMenu: onInit")
        self.action_exitkeys_id = [10, 13]

        self.listControl = self.getControl(3000)
        self.listControl.addItems(self.action_items)
        self.setFocus(self.listControl)

        bg_image = self.getControl(3010)
        bg_image.setHeight(50 * len(self.action_items) + 20)

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onClick(self, controlID):
        if (controlID == 3000):
            self.selected_action = self.listControl.getSelectedItem()
            log.debug("ActionMenu: Selected Item: {0}", self.selected_action)
            self.close()

    def setActionItems(self, action_items):
        self.action_items = action_items

    def getActionItem(self):
        return self.selected_action

