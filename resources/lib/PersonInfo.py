
import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
from DownloadUtils import DownloadUtils

class PersonInfo(xbmcgui.WindowXMLDialog):

    pluginCastLink = ""
    showMovies = False
    personName = ""
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        __settings__ = xbmcaddon.Addon(id='plugin.video.mbcon')
        port = __settings__.getSetting('port')
        host = __settings__.getSetting('ipaddress')
        server = host + ":" + port

        downloadUtils = DownloadUtils()
        
        userid = downloadUtils.getUserId()
        
        jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Persons/" + self.personName + "?format=json", suppress=False, popup=1 )    
        result = json.loads(jsonData)
        
        name = result.get("Name")
        id = result.get("Id")
        
        # other lib items count
        contentCounts = ""
        if(result.get("AdultVideoCount") != None and result.get("AdultVideoCount") > 0):
            contentCounts = contentCounts + "\nAdult Count : " + str(result.get("AdultVideoCount"))
        if(result.get("MovieCount") != None and result.get("MovieCount") > 0):
            contentCounts = contentCounts + "\nMovie Count : " + str(result.get("MovieCount"))    
        if(result.get("SeriesCount") != None and result.get("SeriesCount") > 0):
            contentCounts = contentCounts + "\nSeries Count : " + str(result.get("SeriesCount"))   
        if(result.get("EpisodeCount") != None and result.get("EpisodeCount") > 0):
            contentCounts = contentCounts + "\nEpisode Count : " + str(result.get("EpisodeCount"))      
        
        if(len(contentCounts) > 0):
            contentCounts = "Total Library Counts:" + contentCounts        
        
        #overview
        overview = ""
        if(len(contentCounts) > 0):
            overview = contentCounts + "\n\n"
        over = result.get("Overview")
        if(over == None or over == ""):
            overview = overview + "No details available"
        else:
            overview = overview + over

        #person image
        image = downloadUtils.getArtwork(result, "Primary")
        
        #get other movies
        encoded = name.encode("utf-8")
        encoded = urllib.quote(encoded)
        url = "http://" + server + "/mediabrowser/Users/" + userid + "/Items/?Recursive=True&Person=" + encoded + "&format=json&IsMissing=false"
        xbmc.log("URL: " + url)
        jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1 )
        otherMovieResult = json.loads(jsonData)

        baseName = name.replace(" ", "+")
        baseName = baseName.replace("&", "_")
        baseName = baseName.replace("?", "_")
        baseName = baseName.replace("=", "_")        
        
        #detailsString = getDetailsString()
        #search_url = "http://" + host + ":" + port + "/mediabrowser/Users/" + userid + "/Items/?Recursive=True&Person=PERSON_NAME&Fields=" + detailsString + "&format=json"
        search_url = "http://" + host + ":" + port + "/mediabrowser/Users/" + userid + "/Items/?Recursive=True&Person=PERSON_NAME&format=json"
        search_url = urllib.quote(search_url)
        search_url = search_url.replace("PERSON_NAME", baseName)
        self.pluginCastLink = "XBMC.Container.Update(plugin://plugin.video.mbcon?mode=GET_CONTENT&url=" + search_url + ")"         
        
        otherItemsList = None
        try:
            otherItemsList = self.getControl(3010)
            
            items = otherMovieResult.get("Items")
            if(items == None):
                items = []
            
            for item in items:
                item_id = item.get("Id")
                item_name = item.get("Name")
                
                type_info = ""
                image_id = None
                image_Tag = None
                item_type = item.get("Type")
                
                if(item_type == "Season"):
                    image_id = item.get("SeriesId")
                    image_Tag = item.get("SeriesPrimaryImageTag")
                    season = item.get("IndexNumber")
                    type_info = "Season " + str(season).zfill(2)
                elif(item_type == "Series"):
                    image_id = item.get("Id")
                    imageTags = item.get("ImageTags")
                    if(imageTags != None and imageTags.get("Primary") != None):
                        image_Tag = imageTags.get("Primary")
                    type_info = "Series"                  
                elif(item_type == "Movie"):
                    image_id = item.get("Id")
                    imageTags = item.get("ImageTags")
                    if(imageTags != None and imageTags.get("Primary") != None):
                        image_Tag = imageTags.get("Primary")                    
                    type_info = "Movie"    
                elif(item_type == "Episode"):
                    image_id = item.get("SeriesId")
                    image_Tag = item.get("SeriesPrimaryImageTag")
                    season = item.get("ParentIndexNumber")
                    eppNum = item.get("IndexNumber")
                    type_info = "S" + str(season).zfill(2) + "E" + str(eppNum).zfill(2)
                
                thumbPath = ""
                if(image_Tag != None):
                    thumbPath = downloadUtils.imageUrl(image_id, "Primary", 0, 200, 200, image_Tag)
                    
                #thumbPath = downloadUtils.getArtwork(item, "Primary", width=200, height=200)
                
                listItem = xbmcgui.ListItem(label=item_name, label2=type_info, iconImage=thumbPath, thumbnailImage=thumbPath)
                
                actionUrl = "plugin://plugin.video.mbcon?id=" + item_id + "&mode=ITEM_DETAILS"
                listItem.setProperty("ActionUrl", actionUrl)
                
                otherItemsList.addItem(listItem)
                
        except Exception, e:
            xbmc.log("Exception : " + str(e))
            pass
        
        
        
        # set the dialog data
        self.getControl(3000).setLabel(name)
        self.getControl(3001).setText(overview)
        self.getControl(3009).setImage(image)
        
    def setPersonName(self, name):
        self.personName = name
        
    def setInfo(self, data):
        self.details = data
            
    def onFocus(self, controlId):
        pass
        
    def doAction(self):
        pass

    def closeDialog(self):
        self.close()        
        
    def onClick(self, controlID):

        if(controlID == 3002):
            self.showMovies = True
            
            xbmc.executebuiltin('Dialog.Close(movieinformation)') 
            self.close()
        
        elif(controlID == 3010):
        
            #xbmc.executebuiltin("Dialog.Close(all,true)")
            
            itemList = self.getControl(3010)
            item = itemList.getSelectedItem()
            action = item.getProperty("ActionUrl")        
            
            xbmc.executebuiltin("RunPlugin(" + action + ")")
            
            self.close()

        pass        

