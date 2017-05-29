# Gnu General Public License - see LICENSE.TXT

import xbmcgui

from simple_logging import SimpleLogging
from translation import i18n

log = SimpleLogging(__name__)


class ResumeDialog(xbmcgui.WindowXMLDialog):
    resumePlay = -1
    resumeTimeStamp = ""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        log.info("ResumeDialog INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        self.getControl(3010).setLabel(self.resumeTimeStamp)
        self.getControl(3011).setLabel(i18n('start_from_beginning'))

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def onClick(self, controlID):

        if (controlID == 3010):
            self.resumePlay = 0
            self.close()
        if (controlID == 3011):
            self.resumePlay = 1
            self.close()

        pass

    def setResumeTime(self, timeStamp):
        self.resumeTimeStamp = timeStamp

    def getResumeAction(self):
        return self.resumePlay
