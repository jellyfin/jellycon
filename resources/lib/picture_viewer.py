import xbmc
import xbmcaddon
import xbmcgui

from simple_logging import SimpleLogging

log = SimpleLogging(__name__)

class PictureViewer(xbmcgui.WindowXMLDialog):
    picture_url = None

    def __init__(self, *args, **kwargs):
        log.debug("PictureViewer: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("PictureViewer: onInit")
        self.action_exitkeys_id = [10, 13]

        picture_control = self.getControl(3010)

        picture_control.setImage(self.picture_url)
        #self.listControl.addItems(self.action_items)
        #self.setFocus(self.listControl)

        #bg_image = self.getControl(3010)
        #bg_image.setHeight(50 * len(self.action_items) + 20)

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onClick(self, controlID):
        pass

    def setPicture(self, url):
        self.picture_url = url
