
import os
import xml.etree.ElementTree as etree
import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils

def loadSkinDefaults():

    defaultViewData = {}
    # load current default views
    # add a hash of xbmc.getSkinDir() to file name to make it skin specific
    __addon__ = xbmcaddon.Addon(id='plugin.video.embycon')
    __addondir__ = xbmc.translatePath( __addon__.getAddonInfo('profile'))
    view_list_path = os.path.join(__addondir__, "default_views.json")
    if os.path.exists(view_list_path):
        dataFile = open(view_list_path, 'r')
        jsonData = dataFile.read()
        dataFile.close()
        defaultViewData = json.loads(jsonData)

    return defaultViewData

class DefaultViews(xbmcgui.WindowXMLDialog):
   
    viewCats = ["Movies", "BoxSets", "Trailers", "Series", "Seasons", "Episodes"]
    viewData = {}
    defaultView = {}
      
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        xbmc.log("WINDOW INITIALISED")

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        # load skin views
        skin_view_file = os.path.join(xbmc.translatePath('special://skin'), "views.xml")
        xbmc.log("Loading Skin View List From : " + skin_view_file)
        if os.path.exists(skin_view_file):
            data = etree.parse(skin_view_file).getroot()
            for view in data.iter("view"):
                self.viewData[view.attrib["id"]] = view.attrib["value"]
        
        # load current default views            
        self.defaultView = loadSkinDefaults()
            
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
            
