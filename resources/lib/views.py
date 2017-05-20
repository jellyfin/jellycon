# Gnu General Public License - see LICENSE.TXT

import os
import xml.etree.ElementTree as etree
import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from downloadutils import DownloadUtils
from simple_logging import SimpleLogging

log = SimpleLogging("EmbyCon." + __name__)
__addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
__language__ = __addon__.getLocalizedString

def loadSkinDefaults():

    defaultViewData = {}
    # load current default views
    # add a hash of xbmc.getSkinDir() to file name to make it skin specific
    __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile'))
    view_list_path = os.path.join(__addondir__, "default_views.json")
    if os.path.exists(view_list_path):
        dataFile = open(view_list_path, 'r')
        jsonData = dataFile.read()
        dataFile.close()
        defaultViewData = json.loads(jsonData)

    return defaultViewData

class DefaultViews(xbmcgui.WindowXMLDialog):
   
    viewCats = ["Movies", "BoxSets", "Series", "Seasons", "Episodes"]
    viewData = {}
    defaultView = {}
      
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        log.info("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        # load skin views               
        addonSettings = xbmcaddon.Addon(id='plugin.video.embycon')
        addonPath = addonSettings.getAddonInfo('path')
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
        self.viewData = skin_views
        
        # load current default views            
        self.defaultView = loadSkinDefaults()

        self.getControl(3110).setLabel(__language__(30236))
        self.getControl(3020).setLabel(__language__(30230))
        self.getControl(3021).setLabel(__language__(30231))
        self.getControl(3022).setLabel(__language__(30232))
        self.getControl(3023).setLabel(__language__(30233))
        self.getControl(3024).setLabel(__language__(30234))
        self.getControl(3025).setLabel(__language__(30235))

        # set default values
        name = self.getNameById(self.defaultView.get("Movies"))
        self.getControl(3010).setLabel(name)
        
        name = self.getNameById(self.defaultView.get("BoxSets"))
        self.getControl(3011).setLabel(name)    

        name = self.getNameById(self.defaultView.get("Series"))
        self.getControl(3012).setLabel(name) 

        name = self.getNameById(self.defaultView.get("Seasons"))
        self.getControl(3013).setLabel(name) 

        name = self.getNameById(self.defaultView.get("Episodes"))
        self.getControl(3014).setLabel(name)         
        
    def onFocus(self, controlId):      
        pass
        
    def doAction(self, actionID):
        pass
    
    def getNameById(self, viewId):
        if(viewId == None):
            return "None"
            
        for name, id in self.viewData.iteritems():
            if id == viewId:
                return name
            
        return "None"
    
    def getNextViewName(self, current):
        keys = list(self.viewData.keys())
        if(current not in keys):
            return keys[0]
            
        index = keys.index(current)
        if(index > -1 and index < len(keys)-1):
            return keys[index + 1]
        else:
            return keys[0]

    def onClick(self, controlID):
        
        if(controlID >= 3010 and controlID <= 3014):
            control = self.getControl(controlID)
            control.setLabel(self.getNextViewName(control.getLabel())) 
            
        elif(controlID == 3110):
        
            self.setViewId("Movies", 3010)
            self.setViewId("BoxSets", 3011)
            self.setViewId("Series", 3012)
            self.setViewId("Seasons", 3013)
            self.setViewId("Episodes", 3014)
        
            __addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
            __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile'))
            view_list_path = os.path.join(__addondir__, "default_views.json")
            dataFile = open(view_list_path, 'w')
            stringdata = json.dumps(self.defaultView)
            dataFile.write(stringdata)
            dataFile.close()        

            self.close()
        
        pass
        
    def setViewId(self, viewName, labelId):
        viewId = self.viewData.get(self.getControl(labelId).getLabel())
        if(viewId == None):
            return
        else:
            self.defaultView[viewName] = viewId
            
