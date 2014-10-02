import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc
import threading
import sys

class DisplayItems(xbmcgui.WindowXMLDialog):

    actionThread = None
    
    def __init__(self,strXMLname, strFallbackPath, strDefaultName, forceFallback):
        # Changing the three varibles passed won't change, anything
        # Doing strXMLname = "bah.xml" will not change anything.
        # don't put GUI sensitive stuff here (as the xml hasn't been read yet
        # Idea to initialize your variables here

        pass

    def onInit(self):
        # Put your List Populating code/ and GUI startup stuff here
        self.actionThread = BackgroundItemThread()
        self.actionThread.setWindow(self)
        self.actionThread.start()
        
        pass

    def onAction(self, action):
    
        aId = action.getId()
        #xbmc.log("Windows Action : " + str(aId))
        
        if aId == 10 or aId == 92:
            self.close()
        else:
            pass            

    def onClick(self, controlID):
        """
            Notice: onClick not onControl
            Notice: it gives the ID of the control not the control object
        """
        pass

    def onFocus(self, controlID):
        pass
        
class BackgroundItemThread(threading.Thread):

    rootWindow = None
    
    def setWindow(self, window):
        self.rootWindow = window

    def run(self):
        xbmc.log("BackgroundItemThread Started")
        
        #self.rootWindow.setProperty('content','movies')
        #xbmc.executebuiltin("Container.SetContent(movies)")
        #xbmc.executebuiltin("Container.SetViewMode(522)")

        itemList = self.rootWindow.getControl(50)
               
        thumbPath = "http://192.168.0.27:8096/mediabrowser/Items/924b2d98a64ae17fc31417b3cce02783/Images/Primary/0/0e5801646b3f1b8361a8bc73ff86a9e4/original/10000/10000/0"
        
        for x in range(0, 500):
            listItem = xbmcgui.ListItem(label="Test-" + str(x), label2="Test2-" + str(x), iconImage=thumbPath, thumbnailImage=thumbPath) 

            infolabels = { "title": "My Movie-" + str(x), "Plot": "Some plot inof", "plotoutline": "short plot", "tvshowtitle": "My TV Title", "originaltitle": "Original Title"}
            listItem.setInfo( type="movies", infoLabels=infolabels )
            listItem.setProperty('IsPlayable', 'true')
            
            #selected = itemList.getSelectedItem()
            selected = itemList.getSelectedPosition()
            xbmc.log("SELECTED 01: " + str(selected))
            
            itemList.addItem(listItem)
            
            if(selected != -1):
                #item = itemList.getListItem(selected)
                #selected = itemList.getSelectedItem()
                #xbmc.log("SELECTED 02: " + str(item))
                itemList.selectItem(selected)
                #item.select(True)
            
            xbmc.sleep(200)
        
        

        
        xbmc.log("BackgroundItemThread Exiting")



        