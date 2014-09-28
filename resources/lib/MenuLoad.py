#################################################################################################
# menu item loader thread
# this loads the favourites.xml and sets the windows props for the menus to auto display in skins
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import xml.etree.ElementTree as xml
import os
import threading

class LoadMenuOptionsThread(threading.Thread):

    logLevel = 0
    addonSettings = None
    getString = None

    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.mbcon')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        self.getString = self.addonSettings.getLocalizedString
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("MBCon LoadMenuOptionsThread -> Log Level:" +  str(self.logLevel))
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("MBCon LoadMenuOptionsThread -> " + msg) 
    
    def run(self):
        try:
            self.run_internal()
        except Exception, e:
            xbmcgui.Dialog().ok(self.getString(30205), str(e))
            raise
            
    def run_internal(self):
        self.logMsg("LoadMenuOptionsThread Started")
               
        lastFavPath = ""
        favourites_file = os.path.join(xbmc.translatePath('special://profile'), "favourites.xml")
        self.loadMenuOptions(favourites_file)
        lastFavPath = favourites_file
        
        try:
            lastModLast = os.stat(favourites_file).st_mtime
        except:
            lastModLast = 0;
        
        while (xbmc.abortRequested == False):
            
            favourites_file = os.path.join(xbmc.translatePath('special://profile'), "favourites.xml")
            try:
                lastMod = os.stat(favourites_file).st_mtime
            except:
                lastMod = 0;
            
            if(lastFavPath != favourites_file or lastModLast != lastMod):
                self.loadMenuOptions(favourites_file)
                
            lastFavPath = favourites_file
            lastModLast = lastMod
            
            xbmc.sleep(3000)
                        
        self.logMsg("LoadMenuOptionsThread Exited")

    def loadMenuOptions(self, pathTofavourites):
               
        self.logMsg("LoadMenuOptionsThread -> Loading menu items from : " + pathTofavourites)
        WINDOW = xbmcgui.Window( 10000 )
        menuItem = 0
        
        try:
            tree = xml.parse(pathTofavourites)
            rootElement = tree.getroot()
        except Exception, e:
            self.logMsg("LoadMenuOptionsThread -> Error Parsing favourites.xml : " + str(e), level=0)
            for x in range(0, 10):
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(x), "")
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(x), "")
                WINDOW.setProperty("xbmb3c_menuitem_collection_" + str(x), "")
            return
        
        for child in rootElement.findall('favourite'):
            name = child.get('name')
            action = child.text
        
            if(len(name) > 1 and name[0:1] != '-'):
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(menuItem), name)
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(menuItem), action)
                WINDOW.setProperty("xbmb3c_menuitem_collection_" + str(menuItem), name)
                self.logMsg("xbmb3c_menuitem_name_" + str(menuItem) + " : " + name)
                self.logMsg("xbmb3c_menuitem_action_" + str(menuItem) + " : " + action)
                self.logMsg("xbmb3c_menuitem_collection_" + str(menuItem) + " : " + name)   

                menuItem = menuItem + 1             
            
        for x in range(menuItem, menuItem+10):
                WINDOW.setProperty("xbmb3c_menuitem_name_" + str(x), "")
                WINDOW.setProperty("xbmb3c_menuitem_action_" + str(x), "")
                self.logMsg("xbmb3c_menuitem_name_" + str(x) + " : ")
                self.logMsg("xbmb3c_menuitem_action_" + str(x) + " : ")
                self.logMsg("xbmb3c_menuitem_collection_" + str(x) + " : ")
                

            

    