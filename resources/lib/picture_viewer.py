from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import xbmcgui

from .lazylogger import LazyLogger

log = LazyLogger(__name__)


class PictureViewer(xbmcgui.WindowXMLDialog):
    picture_url = None
    action_exitkeys_id = None

    def __init__(self, *args, **kwargs):
        log.debug("PictureViewer: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.debug("PictureViewer: onInit")
        self.action_exitkeys_id = [10, 13]

        picture_control = self.getControl(3010)

        picture_control.setImage(self.picture_url)

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onClick(self, controlID):
        pass

    def setPicture(self, url):
        self.picture_url = url
