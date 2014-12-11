import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils
import threading

class SearchDialog(xbmcgui.WindowXMLDialog):

    searchThread = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        self.searchThread = BackgroundSearchThread()
        self.searchThread.setDialog(self)
        self.searchThread.start()
        

    def onFocus(self, controlId):
        pass
        
    def onAction(self, action):
        #xbmc.log("onAction : " + str(action.getId()) + " " + str(action.getButtonCode()) + " " + str(action))
        
        ACTION_PREVIOUS_MENU = 10
        ACTION_SELECT_ITEM = 7
        ACTION_PARENT_DIR = 9
        
        if action == ACTION_PREVIOUS_MENU or action.getId() == 92:
            searchTerm = self.getControl(3010).getLabel()
            if(len(searchTerm) == 0):
                self.close()
            else:
                searchTerm = searchTerm[:-1]
                self.getControl(3010).setLabel(searchTerm)
                self.searchThread.setSearch(searchTerm)
    
        #self.getControl(3010).setLabel(str(action.getButtonCode()))


    def closeDialog(self):
        thread.stopRunning()
        self.close()
        
    def onClick(self, controlID):

        if(controlID == 3020):
            self.addCharacter("A")
        elif(controlID == 3021):
            self.addCharacter("B")
        elif(controlID == 3022):
            self.addCharacter("C")
        elif(controlID == 3023):
            self.addCharacter("D")
        elif(controlID == 3024):
            self.addCharacter("E")
        elif(controlID == 3025):
            self.addCharacter("F")
        elif(controlID == 3026):
            self.addCharacter("G")
        elif(controlID == 3027):
            self.addCharacter("H")
        elif(controlID == 3028):
            self.addCharacter("I")
        elif(controlID == 3029):
            self.addCharacter("J")
        elif(controlID == 3030):
            self.addCharacter("K")
        elif(controlID == 3031):
            self.addCharacter("L")
        elif(controlID == 3032):
            self.addCharacter("M")
        elif(controlID == 3033):
            self.addCharacter("N")
        elif(controlID == 3034):
            self.addCharacter("O")
        elif(controlID == 3035):
            self.addCharacter("P")
        elif(controlID == 3036):
            self.addCharacter("Q")
        elif(controlID == 3037):
            self.addCharacter("R")
        elif(controlID == 3038):
            self.addCharacter("S")
        elif(controlID == 3039):
            self.addCharacter("T")
        elif(controlID == 3040):
            self.addCharacter("U")
        elif(controlID == 3041):
            self.addCharacter("V")
        elif(controlID == 3042):
            self.addCharacter("W")
        elif(controlID == 3043):
            self.addCharacter("X")
        elif(controlID == 3044):
            self.addCharacter("Y")
        elif(controlID == 3045):
            self.addCharacter("Z")
        elif(controlID == 3046):
            self.addCharacter("0")    
        elif(controlID == 3047):
            self.addCharacter("1")  
        elif(controlID == 3048):
            self.addCharacter("2")  
        elif(controlID == 3049):
            self.addCharacter("3")  
        elif(controlID == 3050):
            self.addCharacter("4")  
        elif(controlID == 3051):
            self.addCharacter("5")  
        elif(controlID == 3052):
            self.addCharacter("6")  
        elif(controlID == 3053):
            self.addCharacter("7")  
        elif(controlID == 3054):
            self.addCharacter("8")  
        elif(controlID == 3055):
            self.addCharacter("9")  
        elif(controlID == 3056):
            searchTerm = self.getControl(3010).getLabel()
            searchTerm = searchTerm[:-1]
            self.getControl(3010).setLabel(searchTerm)
            self.searchThread.setSearch(searchTerm)
        elif(controlID == 3057):
            self.addCharacter(" ")
        elif(controlID == 3058):
            self.getControl(3010).setLabel("")
            self.searchThread.setSearch("")
            
        elif(controlID == 3110):
        
            #xbmc.executebuiltin("Dialog.Close(all,true)")
            itemList = self.getControl(3110)
            item = itemList.getSelectedItem()
            action = item.getProperty("ActionUrl")
            xbmc.executebuiltin("RunPlugin(" + action + ")")
        elif(controlID == 3111):
        
            #xbmc.executebuiltin("Dialog.Close(all,true)")
            itemList = self.getControl(3111)
            item = itemList.getSelectedItem()
            action = item.getProperty("ActionUrl")
            xbmc.executebuiltin("RunPlugin(" + action + ")")            
        elif(controlID == 3112):
        
            #xbmc.executebuiltin("Dialog.Close(all,true)")
            itemList = self.getControl(3112)
            item = itemList.getSelectedItem()
            action = item.getProperty("ActionUrl")
            xbmc.executebuiltin("RunPlugin(" + action + ")")            
            
        pass

    def addCharacter(self, char):
        searchTerm = self.getControl(3010).getLabel()
        searchTerm = searchTerm + char
        self.getControl(3010).setLabel(searchTerm)
        self.searchThread.setSearch(searchTerm)
        
class BackgroundSearchThread(threading.Thread):
 
    active = True
    searchDialog = None
    searchString = ""

    def __init__(self, *args):
        xbmc.log("BackgroundSearchThread Init")
        threading.Thread.__init__(self, *args)

    def setSearch(self, searchFor):
        self.searchString = searchFor
        
    def stopRunning(self):
        self.active = False
        
    def setDialog(self, searchDialog):
        self.searchDialog = searchDialog
        
    def run(self):
        xbmc.log("BackgroundSearchThread Started")     
        
        lastSearchString = ""
        
        while(xbmc.abortRequested == False and self.active == True):
            currentSearch = self.searchString  
            if(currentSearch != lastSearchString):
                lastSearchString = currentSearch
                self.doSearch(currentSearch)

            xbmc.sleep(2000)

        xbmc.log("BackgroundSearchThread Exited")
        
    def doSearch(self, searchTerm):

        movieResultsList = self.searchDialog.getControl(3110)
        while(movieResultsList.size() > 0):
            movieResultsList.removeItem(0)
        #movieResultsList.reset()
    
    
        seriesResultsList = self.searchDialog.getControl(3111)
        while(seriesResultsList.size() > 0):
            seriesResultsList.removeItem(0)
        #seriesResultsList.reset()

        episodeResultsList = self.searchDialog.getControl(3112)
        while(episodeResultsList.size() > 0):
            episodeResultsList.removeItem(0)
        #episodeResultsList.reset()
       
        if(len(searchTerm) == 0):
            return
        
        __settings__ = xbmcaddon.Addon(id='plugin.video.mbcon')
        port = __settings__.getSetting('port')
        host = __settings__.getSetting('ipaddress')
        server = host + ":" + port
        
        downloadUtils = DownloadUtils()
        
        #
        # Process movies
        #
        search = urllib.quote(searchTerm)
        url = "http://" + server + "/mediabrowser/Search/Hints?SearchTerm=" + search + "&Limit=10&IncludeItemTypes=Movie&format=json"
        jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1) 
        result = json.loads(jsonData)
            
        items = result.get("SearchHints")
        
        if(items == None or len(items) == 0):
            item = []
            
        for item in items:
            xbmc.log(str(item))
        
            item_id = item.get("ItemId")
            item_name = item.get("Name")
            item_type = item.get("Type")
            
            typeLabel = "Movie"
            
            thumbPath = downloadUtils.imageUrl(item_id, "Primary", 0, 200, 200)
            xbmc.log(thumbPath)
            
            listItem = xbmcgui.ListItem(label=item_name, label2=typeLabel, iconImage=thumbPath, thumbnailImage=thumbPath)
            
            actionUrl = "plugin://plugin.video.mbcon?id=" + item_id + "&mode=ITEM_DETAILS"
            listItem.setProperty("ActionUrl", actionUrl)
            
            movieResultsList.addItem(listItem)    
            
        #
        # Process series
        #
        search = urllib.quote(searchTerm)
        url = "http://" + server + "/mediabrowser/Search/Hints?SearchTerm=" + search + "&Limit=10&IncludeItemTypes=Series&format=json"
        jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1 ) 
        result = json.loads(jsonData)
            
        items = result.get("SearchHints")
        
        if(items == None or len(items) == 0):
            item = []
            
        for item in items:
            xbmc.log(str(item))
        
            item_id = item.get("ItemId")
            item_name = item.get("Name")
            item_type = item.get("Type")
            
            typeLabel = ""
            image_id = ""
            
            image_id = item.get("ItemId")
            typeLabel = "Series"                  
                    
            thumbPath = downloadUtils.imageUrl(image_id, "Primary", 0, 200, 200)
            xbmc.log(thumbPath)
            
            listItem = xbmcgui.ListItem(label=item_name, label2=typeLabel, iconImage=thumbPath, thumbnailImage=thumbPath)
            
            actionUrl = "plugin://plugin.video.mbcon?id=" + item_id + "&mode=ITEM_DETAILS"
            listItem.setProperty("ActionUrl", actionUrl)
            
            seriesResultsList.addItem(listItem) 

        #
        # Process episodes
        #
        search = urllib.quote(searchTerm)
        url = "http://" + server + "/mediabrowser/Search/Hints?SearchTerm=" + search + "&Limit=10&IncludeItemTypes=Episode&format=json"
        jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1 ) 
        result = json.loads(jsonData)
            
        items = result.get("SearchHints")
        
        if(items == None or len(items) == 0):
            item = []
            
        for item in items:
            xbmc.log(str(item))
        
            item_id = item.get("ItemId")
            item_name = item.get("Name")
            item_type = item.get("Type")
            
            image_id = item.get("ThumbImageItemId")
            season = item.get("ParentIndexNumber")
            eppNum = item.get("IndexNumber")
            typeLabel = "S" + str(season).zfill(2) + "E" + str(eppNum).zfill(2)
                    
            thumbPath = downloadUtils.imageUrl(image_id, "Primary", 0, 200, 200)
            
            xbmc.log(thumbPath)
            
            listItem = xbmcgui.ListItem(label=item_name, label2=typeLabel, iconImage=thumbPath, thumbnailImage=thumbPath)
            
            actionUrl = "plugin://plugin.video.mbcon?id=" + item_id + "&mode=ITEM_DETAILS"
            listItem.setProperty("ActionUrl", actionUrl)
            
            episodeResultsList.addItem(listItem)                            
        
        