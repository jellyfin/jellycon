# Gnu General Public License - see LICENSE.TXT

import os
import xbmc
import xbmcgui
import xbmcaddon

import json

from simple_logging import SimpleLogging
from translation import i18n

log = SimpleLogging(__name__)
__addon__ = xbmcaddon.Addon(id='plugin.video.embycon')


def loadSkinDefaults():
    defaultData = {}
    # load current default views
    # add a hash of xbmc.getSkinDir() to file name to make it skin specific
    __addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
    view_list_path = os.path.join(__addondir__, "default_views.json")
    if os.path.exists(view_list_path):
        dataFile = open(view_list_path, 'r')
        jsonData = dataFile.read()
        dataFile.close()
        defaultData = json.loads(jsonData)

    return defaultData


class DefaultViews(xbmcgui.WindowXMLDialog):
    viewData = {}
    sortData = {"Title": "title", "Date": "date"}
    defaultView = {}
    defaultSort = {}

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        log.info("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        # load skin views               
        addonPath = __addon__.getAddonInfo('path')
        skin_view_file = os.path.join(addonPath, "resources", "data", "skin_views.json")
        log.info("Loading skin views form: " + skin_view_file)
        dataFile = open(skin_view_file, 'r')
        jsonData = dataFile.read()
        dataFile.close()
        defaultViewData = json.loads(jsonData)
        log.info("Loaded skin views: " + str(defaultViewData))
        skin_used = xbmc.getSkinDir()
        log.info("Current skin: " + skin_used)
        skin_views = defaultViewData.get(skin_used, None)
        log.info("Current skin views: " + str(skin_views))
        if skin_views is None:
            xbmcgui.Dialog().notification(__addon__.getAddonInfo('name'), i18n('skin_not_supported') % skin_used, icon='special://home/addons/plugin.video.embycon/icon.png')
            self.close()
            return
        self.viewData = skin_views

        # load current default views
        savedData = loadSkinDefaults()
        self.defaultView = savedData.get("view", {})
        self.defaultSort = savedData.get("sort", {})

        self.getControl(3110).setLabel(i18n('save'))
        self.getControl(3019).setLabel(i18n('default_sort'))
        self.getControl(3020).setLabel(i18n('default_view'))
        self.getControl(3021).setLabel(i18n('movies'))
        self.getControl(3022).setLabel(i18n('boxsets'))
        self.getControl(3023).setLabel(i18n('series'))
        self.getControl(3024).setLabel(i18n('seasons'))
        self.getControl(3025).setLabel(i18n('episodes'))

        # set default values
        name = self.getViewNameById(self.defaultView.get("Movies"))
        self.getControl(3010).setLabel(name)
        name = self.getViewNameById(self.defaultView.get("BoxSets"))
        self.getControl(3011).setLabel(name)
        name = self.getViewNameById(self.defaultView.get("Series"))
        self.getControl(3012).setLabel(name)
        name = self.getViewNameById(self.defaultView.get("Seasons"))
        self.getControl(3013).setLabel(name)
        name = self.getViewNameById(self.defaultView.get("Episodes"))
        self.getControl(3014).setLabel(name)

        name = self.getSortNameById(self.defaultSort.get("Movies"))
        self.getControl(3050).setLabel(name)
        name = self.getSortNameById(self.defaultSort.get("BoxSets"))
        self.getControl(3051).setLabel(name)
        name = self.getSortNameById(self.defaultSort.get("Series"))
        self.getControl(3052).setLabel(name)
        name = self.getSortNameById(self.defaultSort.get("Seasons"))
        self.getControl(3053).setLabel(name)
        name = self.getSortNameById(self.defaultSort.get("Episodes"))
        self.getControl(3054).setLabel(name)

    def onFocus(self, controlId):
        pass

    def doAction(self, actionID):
        pass

    def getSortNameById(self, sortId):
        if (sortId == None):
            return "None"

        for name, id in self.sortData.iteritems():
            if id == sortId:
                return name

        return "None"

    def getViewNameById(self, viewId):
        if (viewId == None):
            return "None"

        for name, id in self.viewData.iteritems():
            if id == viewId:
                return name

        return "None"

    def getNextViewName(self, current):
        keys = list(self.viewData.keys())
        if (current not in keys):
            return keys[0]

        index = keys.index(current)
        if (index > -1 and index < len(keys) - 1):
            return keys[index + 1]
        else:
            return keys[0]

    def getNextSortName(self, current):
        keys = list(self.sortData.keys())
        if (current not in keys):
            return keys[0]

        index = keys.index(current)
        if (index > -1 and index < len(keys) - 1):
            return keys[index + 1]
        else:
            return keys[0]

    def onClick(self, controlID):

        if controlID >= 3010 and controlID <= 3014:
            control = self.getControl(controlID)
            control.setLabel(self.getNextViewName(control.getLabel()))

        elif controlID >= 3050 and controlID <= 3054:
            control = self.getControl(controlID)
            control.setLabel(self.getNextSortName(control.getLabel()))

        elif controlID == 3110:

            self.setViewId("Movies", 3010)
            self.setViewId("BoxSets", 3011)
            self.setViewId("Series", 3012)
            self.setViewId("Seasons", 3013)
            self.setViewId("Episodes", 3014)

            self.setSortId("Movies", 3050)
            self.setSortId("BoxSets", 3051)
            self.setSortId("Series", 3052)
            self.setSortId("Seasons", 3053)
            self.setSortId("Episodes", 3054)

            __addondir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
            view_list_path = os.path.join(__addondir__, "default_views.json")
            dataFile = open(view_list_path, 'w')
            defaults_data = {"view": self.defaultView, "sort": self.defaultSort}
            stringdata = json.dumps(defaults_data)
            dataFile.write(stringdata)
            dataFile.close()

            self.close()

        pass

    def setViewId(self, viewName, labelId):
        viewId = self.viewData.get(self.getControl(labelId).getLabel())
        if (viewId == None):
            return
        else:
            self.defaultView[viewName] = viewId

    def setSortId(self, sortName, labelId):
        sortId = self.sortData.get(self.getControl(labelId).getLabel())
        if (sortId == None):
            return
        else:
            self.defaultSort[sortName] = sortId
