'''
    @license    : Gnu General Public License - see LICENSE.TXT

    This is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with software.  If not, see <http://www.gnu.org/licenses/>.
    
    Thanks to Hippojay for the PleXBMC plugin this is derived from
    This software is derived form the XBMB3C addon
    
'''

import struct
import urllib
import glob
import re
import hashlib
import xbmcplugin
import xbmcgui
import xbmcaddon
import httplib
import socket
import sys
import os
import time
import inspect
import base64
import random
import datetime
import requests
from urlparse import urlparse
import cProfile
import pstats
import threading
import hashlib
import StringIO
import gzip
import xml.etree.ElementTree as etree

__settings__ = xbmcaddon.Addon(id='plugin.video.mbcon')
__cwd__ = __settings__.getAddonInfo('path')
__addon__       = xbmcaddon.Addon(id='plugin.video.mbcon')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ) 
__language__     = __addon__.getLocalizedString

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append(BASE_RESOURCE_PATH)
PLUGINPATH = xbmc.translatePath( os.path.join( __cwd__) )

ProfileCode = __settings__.getSetting('profile') == "true"

if(ProfileCode):
    xbmcgui.Dialog().ok(__language__(30201), __language__(30202), __language__(30203))
    pr = cProfile.Profile()
    pr.enable()
    
from DownloadUtils import DownloadUtils
from ItemInfo import ItemInfo
from Utils import PlayUtils
from ClientInformation import ClientInformation
from PersonInfo import PersonInfo
from SearchDialog import SearchDialog
from DisplayItems import DisplayItems

ADDON_VERSION = ClientInformation().getVersion()

xbmc.log ("===== MBCon START =====")

xbmc.log ("MBCon -> running Python: " + str(sys.version_info))
xbmc.log ("MBCon -> running MBCon: " + str(ADDON_VERSION))
xbmc.log (xbmc.getInfoLabel( "System.BuildVersion" ))

#Get the setting from the appropriate file.
CP_ADD_URL = 'XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add?title=%s)'
_MODE_GETCONTENT=0
_MODE_MOVIES=0
_MODE_SEARCH=2
_MODE_SETVIEWS=3
_MODE_SHOW_SECTIONS=4
_MODE_BASICPLAY=12
_MODE_CAST_LIST=14
_MODE_PERSON_DETAILS=15
_MODE_WIDGET_CONTENT=16
_MODE_ITEM_DETAILS=17
_MODE_SHOW_SEARCH=18
_MODE_SHOW_PARENT_CONTENT=21

#Check debug first...
logLevel = 0
try:
    logLevel = int(__settings__.getSetting('logLevel'))   
except:
    pass

import json as json
   
#define our global download utils
downloadUtils = DownloadUtils()

def printDebug( msg, level = 1):
    if(logLevel >= level):
        if(logLevel == 2):
            stackline = ""
            stack = inspect.stack()
            for frame in stack: 
                stackline = stackline + "." + frame[3]        
            xbmc.log("MBCon " + str(level) + " -> (" + stackline + ") : " + str(msg))
        else:
            xbmc.log("MBCon " + str(level) + " -> " + str(msg))

def getAuthHeader():
    txt_mac = downloadUtils.getMachineId()
    version = ClientInformation().getVersion()
    userid = xbmcgui.Window( 10000 ).getProperty("userid")
    deviceName = __settings__.getSetting('deviceName')
    deviceName = deviceName.replace("\"", "_")
    authString = "MediaBrowser UserId=\"" + userid + "\",Client=\"XBMC\",Device=\"" + deviceName + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
    headers = {'Accept-encoding': 'gzip', 'Authorization' : authString}
    xbmc.log("MBCon Authentication Header : " + str(headers))
    return headers 
            
def getPlatform( ):

    if xbmc.getCondVisibility('system.platform.osx'):
        return "OSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return "ATV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux/RPi"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Linux/Android"

    return "Unknown"

ADDON_PLATFORM = getPlatform()
xbmc.log ("MBCon -> Platform: " + str(ADDON_PLATFORM))

g_flatten = __settings__.getSetting('flatten')
printDebug("MBCon -> Flatten is: " + g_flatten)

xbmc.log ("MBCon -> LogLevel:  " + str(logLevel))

g_contextReplace=True

g_loc = "special://home/addons/plugin.video.mbcon"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)',
              }

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None

genreList=[__language__(30069),__language__(30070),__language__(30071),__language__(30072),__language__(30073),__language__(30074),__language__(30075),__language__(30076),__language__(30077),__language__(30078),__language__(30079),__language__(30080),__language__(30081),__language__(30082),__language__(30083),__language__(30084),__language__(30085),__language__(30086),__language__(30087),__language__(30088),__language__(30089)]
sortbyList=[__language__(30059),__language__(30060),__language__(30061),__language__(30062),__language__(30063),__language__(30064),__language__(30065),__language__(30066),__language__(30067)]

def getServerDetails():

    printDebug("Getting Server Details from Network")

    MESSAGE = "who is MediaBrowserServer?"
    MULTI_GROUP = ("<broadcast>", 7359)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(6.0)
    
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.SO_REUSEADDR, 1)
    
    xbmc.log("MutliGroup       : " + str(MULTI_GROUP));
    xbmc.log("Sending UDP Data : " + MESSAGE);
    sock.sendto(MESSAGE, MULTI_GROUP)

    try:
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        xbmc.log("Received Response : " + data)
        if(data[0:18] == "MediaBrowserServer"):
            xbmc.log("Found Server : " + data[19:])
            return data[19:]
    except:
        xbmc.log("No UDP Response")
        pass
    
    return None
   
def getCollections(detailsString):
    printDebug("== ENTER: getCollections ==")
    
    MB_server = __settings__.getSetting('ipaddress')+":"+__settings__.getSetting('port')

    userid = downloadUtils.getUserId()
    
    if(userid == None or len(userid) == 0):
        return {}
    
    try:
        jsonData = downloadUtils.downloadUrl(MB_server + "/mediabrowser/Users/" + userid + "/Items/Root?format=json")
    except Exception, msg:
        error = "Get connect : " + str(msg)
        xbmc.log (error)
        return {}        
    
    printDebug("jsonData : " + jsonData, level=2)
    result = json.loads(jsonData)
    
    parentid = result.get("Id")
    printDebug("parentid : " + parentid)
       
    htmlpath = ("http://%s/mediabrowser/Users/" % MB_server)
    jsonData = downloadUtils.downloadUrl(htmlpath + userid + "/items?ParentId=" + parentid + "&Sortby=SortName&format=json")
    printDebug("jsonData : " + jsonData, level=2)
    collections=[]

    if jsonData is False:
        return {}

    result = json.loads(jsonData)
    result = result.get("Items")
    
    for item in result:
        if(item.get("RecursiveItemCount") != "0"):
            Name =(item.get("Name")).encode('utf-8')
            if __settings__.getSetting(urllib.quote('sortbyfor'+Name)) == '':
                __settings__.setSetting(urllib.quote('sortbyfor'+Name),'SortName')
                __settings__.setSetting(urllib.quote('sortorderfor'+Name),'Ascending')
            
            total = str(item.get("RecursiveItemCount"))
            section = item.get("CollectionType")
            if (section == None):
              section = "movies"
            collections.append( {'title'      : Name,
                    'address'           : MB_server ,
                    'thumb'             : downloadUtils.getArtwork(item,"Primary") ,
                    'fanart_image'      : downloadUtils.getArtwork(item, "Backdrop") ,
                    'poster'            : downloadUtils.getArtwork(item,"Primary") ,
                    'sectype'           : section,
                    'section'           : section,
                    'guiid'             : item.get("Id"),
                    'path'              : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&IsVirtualUnaired=false&IsMissing=False&Fields=' + detailsString + '&SortOrder='+__settings__.getSetting('sortorderfor'+urllib.quote(Name))+'&SortBy='+__settings__.getSetting('sortbyfor'+urllib.quote(Name))+'&Genres=&format=json'),
                    'collapsed_path'    : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&IsVirtualUnaired=false&IsMissing=False&Fields=' + detailsString + '&SortOrder='+__settings__.getSetting('sortorderfor'+urllib.quote(Name))+'&SortBy='+__settings__.getSetting('sortbyfor'+urllib.quote(Name))+'&Genres=&format=json&CollapseBoxSetItems=true'),
                    'recent_path'       : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") + '&Limit=' + __settings__.getSetting("numRecentMovies") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsNotFolder&ExcludeLocationTypes=Virtual&format=json'),
                    'inprogress_path'   : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") +'&Recursive=true&SortBy=DatePlayed&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsResumable&ExcludeLocationTypes=Virtual&format=json'),
                    'genre_path'        : ('/mediabrowser/Genres?Userid=' + userid + '&parentId=' + item.get("Id") +'&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Recursive=true&format=json'),
                    'nextepisodes_path' : ('/mediabrowser/Shows/NextUp/?Userid=' + userid + '&parentId=' + item.get("Id") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsUnplayed&IsVirtualUnaired=false&IsMissing=False&ExcludeLocationTypes=Virtual&IncludeItemTypes=Episode&format=json'),
                    'unwatched_path'    : ('/mediabrowser/Users/' + userid + '/items?ParentId=' + item.get("Id") +'&Recursive=true&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsNotFolder,IsUnplayed&ExcludeLocationTypes=Virtual&format=json')})

            printDebug("Title " + Name)    
    
    # Add standard nodes
    collections.append({'title':__language__(30170), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Movie&format=json' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30171), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=Series&format=json','thumb':'', 'poster':'', 'fanart_image':'' , 'guiid':''})
    collections.append({'title':__language__(30172), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?&SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&IncludeItemTypes=MusicArtist&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })   
    collections.append({'title':__language__(30173), 'sectype' : 'std.channels', 'section' : 'channels' , 'address' : MB_server , 'path' : '/mediabrowser/Channels?' + userid +'&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':'' })   
    collections.append({'title':__language__(30174), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMovies") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IncludeItemTypes=Movie&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30175), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentTV") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30176), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMusic") +'&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed&IncludeItemTypes=MusicAlbum&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30177), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Movie&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30178), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsResumable&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30179), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Shows/NextUp/?Userid=' + userid + '&Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsUnplayed,IsNotFolder&IsVirtualUnaired=false&IsMissing=False&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30180), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=sortName&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsFavorite,IsNotFolder&IncludeItemTypes=Movie&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30181), 'sectype' : 'std.tvshows', 'section' : 'tvshows'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=sortName&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsFavorite&IncludeItemTypes=Series&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})    
    collections.append({'title':__language__(30182), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=DateCreated&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsNotFolder,IsFavorite&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30183), 'sectype' : 'std.music', 'section' : 'music' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=' + __settings__.getSetting("numRecentMusic") + '&Recursive=true&SortBy=PlayCount&Fields=' + detailsString + '&SortOrder=Descending&Filters=IsPlayed&IncludeItemTypes=MusicAlbum&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30184), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=PremiereDate&Fields=' + detailsString + '&SortOrder=Ascending&Filters=IsUnplayed&IsVirtualUnaired=true&IsNotFolder&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30185), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Recursive=true&SortBy=SortName&Fields=' + detailsString + '&SortOrder=Ascending&IncludeItemTypes=BoxSet&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})

    collections.append({'title':__language__(30189), 'sectype' : 'std.movies', 'section' : 'movies'  , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?SortBy=SortName&Fields=' + detailsString + '&Recursive=true&SortOrder=Ascending&Filters=IsUnplayed&IncludeItemTypes=Movie&format=json' ,'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
    collections.append({'title':__language__(30193), 'sectype' : 'std.tvshows', 'section' : 'tvshows' , 'address' : MB_server , 'path' : '/mediabrowser/Users/' + userid + '/Items?Limit=50&Recursive=true&SortBy=DatePlayed&SortOrder=Descending&Fields=' + detailsString + '&Filters=IsUnplayed&IncludeItemTypes=Episode&format=json','thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
        
    collections.append({'title':__language__(30199), 'sectype' : 'std.setviews', 'section' : 'setviews'  , 'address' : 'SETVIEWS', 'path': 'SETVIEWS', 'thumb':'', 'poster':'', 'fanart_image':'', 'guiid':''})
        
    return collections

def markWatched (url):
    resp = requests.delete(url, data='', headers=getAuthHeader()) # mark unwatched first to reset any play position
    resp = requests.post(url, data='', headers=getAuthHeader())
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")  
    xbmc.executebuiltin("Container.Refresh")

def markUnwatched (url):
    resp = requests.delete(url, data='', headers=getAuthHeader())
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")      
    xbmc.executebuiltin("Container.Refresh")

def markFavorite (url):
    resp = requests.post(url, data='', headers=getAuthHeader())
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")    
    xbmc.executebuiltin("Container.Refresh")
    
def unmarkFavorite (url):
    resp = requests.delete(url, data='', headers=getAuthHeader())
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")    
    xbmc.executebuiltin("Container.Refresh")

def sortby ():
    sortOptions=["", "SortName","ProductionYear,SortName","PremiereDate,SortName","DateCreated,SortName","CriticRating,SortName","CommunityRating,SortName","PlayCount,SortName","Budget,SortName"]
    sortOptionsText=sortbyList
    return_value=xbmcgui.Dialog().select(__language__(30068),sortOptionsText)
    WINDOW = xbmcgui.Window( 10000 )
    __settings__.setSetting('sortbyfor'+urllib.quote(WINDOW.getProperty("heading")),sortOptions[return_value]+',SortName')
    newurl=re.sub("SortBy.*?&","SortBy="+ sortOptions[return_value] + "&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.mbcon/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

def genrefilter ():
    genreFilters=["","Action","Adventure","Animation","Crime","Comedy","Documentary","Drama","Fantasy","Foreign","History","Horror","Music","Musical","Mystery","Romance","Science%20Fiction","Short","Suspense","Thriller","Western"]
    genreFiltersText=genreList#["None","Action","Adventure","Animation","Crime","Comedy","Documentary","Drama","Fantasy","Foreign","History","Horror","Music","Musical","Mystery","Romance","Science Fiction","Short","Suspense","Thriller","Western"]
    return_value=xbmcgui.Dialog().select(__language__(30090),genreFiltersText)
    newurl=re.sub("Genres.*?&","Genres="+ genreFilters[return_value] + "&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.mbcon/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

def sortorder ():
    WINDOW = xbmcgui.Window( 10000 )
    if(__settings__.getSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")))=="Ascending"):
        __settings__.setSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")),'Descending')
        newurl=re.sub("SortOrder.*?&","SortOrder=Descending&",WINDOW.getProperty("currenturl"))
    else:
        __settings__.setSetting('sortorderfor'+urllib.quote(WINDOW.getProperty("heading")),'Ascending')
        newurl=re.sub("SortOrder.*?&","SortOrder=Ascending&",WINDOW.getProperty("currenturl"))
    WINDOW.setProperty("currenturl",newurl)
    u=urllib.quote(newurl)+'&mode=0'
    xbmc.executebuiltin("Container.Update(plugin://plugin.video.mbcon/?url="+u+",\"replace\")")#, WINDOW.getProperty('currenturl')

    
def delete (url):
    return_value = xbmcgui.Dialog().yesno(__language__(30091),__language__(30092))
    if return_value:
        printDebug('Deleting via URL: ' + url)
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30052), __language__(30053))
        resp = requests.delete(url, data='', headers=getAuthHeader())
        deleteSleep=0
        while deleteSleep<10:
            xbmc.sleep(1000)
            deleteSleep=deleteSleep+1
            progress.update(deleteSleep*10,__language__(30053))
        progress.close()
        xbmc.executebuiltin("Container.Refresh")
               
def addGUIItem( url, details, extraData, folder=True ):

    url = url.encode('utf-8')

    printDebug("Adding GuiItem for [%s]" % details.get('title','Unknown'), level=2)
    printDebug("Passed details: " + str(details), level=2)
    printDebug("Passed extraData: " + str(extraData), level=2)
    #printDebug("urladdgui:" + str(url))
    if details.get('title','') == '':
        return

    if extraData.get('mode',None) is None:
        mode="&mode=0"
    else:
        mode="&mode=%s" % extraData['mode']
    
    # play or show info
    selectAction = __settings__.getSetting('selectAction')

    #Create the URL to pass to the item
    if 'mediabrowser/Videos' in url:
        if(selectAction == "1"):
            u = sys.argv[0] + "?id=" + extraData.get('id') + "&mode=" + str(_MODE_ITEM_DETAILS)
        else:
            u = sys.argv[0] + "?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
    elif 'mediabrowser/Search' in url:
        u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_SEARCH)
    elif 'SETVIEWS' in url:
        u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_SETVIEWS)     
    elif url.startswith('http') or url.startswith('file'):
        u = sys.argv[0]+"?url="+urllib.quote(url)+mode
    else:
        if(selectAction == "1"):
            u = sys.argv[0] + "?id=" + extraData.get('id') + "&mode=" + str(_MODE_ITEM_DETAILS)
        else:
            u = sys.argv[0]+"?url=" + url + '&mode=' + str(_MODE_BASICPLAY)

    #Create the ListItem that will be displayed
    thumbPath=str(extraData.get('thumb',''))
    
    addCounts = __settings__.getSetting('addCounts') == 'true'
    
    WINDOW = xbmcgui.Window( 10000 )
    if WINDOW.getProperty("addshowname") == "true":
        if extraData.get('locationtype')== "Virtual":
            listItemName = extraData.get('premieredate').decode("utf-8") + u" - " + details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + details.get('season').decode("utf-8") + u"E" + details.get('title','Unknown').decode("utf-8")
            if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
            list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
        else:
            if details.get('season') == None:
                season = '0'
            else:
                season = details.get('season')
            listItemName = details.get('SeriesName','').decode("utf-8") + u" - " + u"S" + season + u"E" + details.get('title','Unknown').decode("utf-8")
            if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
                listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
            list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
    else:
        listItemName = details.get('title','Unknown')
        if(addCounts and extraData.get("RecursiveItemCount") != None and extraData.get("RecursiveUnplayedItemCount") != None):
            listItemName = listItemName + " (" + str(extraData.get("RecursiveItemCount") - extraData.get("RecursiveUnplayedItemCount")) + "/" + str(extraData.get("RecursiveItemCount")) + ")"
        list = xbmcgui.ListItem(listItemName, iconImage=thumbPath, thumbnailImage=thumbPath)
    printDebug("Setting thumbnail as " + thumbPath, level=2)
    
    # calculate percentage
    cappedPercentage = None
    if (extraData.get('resumetime') != None and int(extraData.get('resumetime')) > 0):
        duration = float(extraData.get('duration'))
        if(duration > 0):
            resume = float(extraData.get('resumetime')) / 60.0
            percentage = int((resume / duration) * 100.0)
            cappedPercentage = percentage - (percentage % 10)
            if(cappedPercentage == 0):
                cappedPercentage = 10
            if(cappedPercentage == 100):
                cappedPercentage = 90
            list.setProperty("complete_percentage", str(cappedPercentage))          
     
    # add resume percentage text to titles
    addResumePercent = __settings__.getSetting('addResumePercent') == 'true'
    if (addResumePercent and details.get('title') != None and cappedPercentage != None):
        details['title'] = details.get('title') + " (" + str(cappedPercentage) + "%)"
    
    #Set the properties of the item, such as summary, name, season, etc
    #list.setInfo( type=extraData.get('type','Video'), infoLabels=details )
    
    #For all end items    
    if ( not folder):
        #list.setProperty('IsPlayable', 'true')
        if extraData.get('type','video').lower() == "video":
            list.setProperty('TotalTime', str(extraData.get('duration')))
            list.setProperty('ResumeTime', str(extraData.get('resumetime')))
    
    artTypes=['poster', 'fanart_image', 'clearlogo', 'discart', 'banner', 'clearart', 'landscape', 'small_poster',  'medium_poster','small_fanartimage', 'medium_fanartimage', 'medium_landscape']
    
    for artType in artTypes:
        imagePath=str(extraData.get(artType,''))
        list=setArt(list,artType, imagePath)
        printDebug( "Setting " + artType + " as " + imagePath, level=2)
    
    menuItems = addContextMenu(details, extraData, folder)
    if(len(menuItems) > 0):
        list.addContextMenuItems( menuItems, g_contextReplace )

    # new way
    videoInfoLabels = {}
    
    if(extraData.get('type') == None or extraData.get('type') == "Video"):
        videoInfoLabels.update(details)
    else:
        list.setInfo( type = extraData.get('type','Video'), infoLabels = details )
    
    videoInfoLabels["duration"] = extraData.get("duration")
    videoInfoLabels["playcount"] = extraData.get("playcount")
    if (extraData.get('favorite') == 'true'):
        videoInfoLabels["top250"] = "1"    
        
    videoInfoLabels["mpaa"] = extraData.get('mpaa')
    videoInfoLabels["rating"] = extraData.get('rating')
    videoInfoLabels["director"] = extraData.get('director')
    videoInfoLabels["writer"] = extraData.get('writer')
    videoInfoLabels["year"] = extraData.get('year')
    videoInfoLabels["studio"] = extraData.get('studio')
    videoInfoLabels["genre"] = extraData.get('genre')
    
    videoInfoLabels["episode"] = details.get('episode')
    videoInfoLabels["season"] = details.get('season') 
    
    list.setInfo('video', videoInfoLabels)
    
    list.addStreamInfo('video', {'duration': extraData.get('duration'), 'aspect': extraData.get('aspectratio'),'codec': extraData.get('videocodec'), 'width' : extraData.get('width'), 'height' : extraData.get('height')})
    list.addStreamInfo('audio', {'codec': extraData.get('audiocodec'),'channels': extraData.get('channels')})
    
    list.setProperty('CriticRating', str(extraData.get('criticrating')))
    list.setProperty('ItemType', extraData.get('itemtype'))
    if extraData.get('totaltime') != None:
        list.setProperty('TotalTime', extraData.get('totaltime'))
    if extraData.get('TotalSeasons')!=None:
        list.setProperty('TotalSeasons',extraData.get('TotalSeasons'))
    if extraData.get('TotalEpisodes')!=None:  
        list.setProperty('TotalEpisodes',extraData.get('TotalEpisodes'))
    if extraData.get('WatchedEpisodes')!=None:
        list.setProperty('WatchedEpisodes',extraData.get('WatchedEpisodes'))
    if extraData.get('UnWatchedEpisodes')!=None:
        list.setProperty('UnWatchedEpisodes',extraData.get('UnWatchedEpisodes'))
    if extraData.get('NumEpisodes')!=None:
        list.setProperty('NumEpisodes',extraData.get('NumEpisodes'))
    
    pluginCastLink = "plugin://plugin.video.mbcon?mode=" + str(_MODE_CAST_LIST) + "&id=" + str(extraData.get('id'))
    list.setProperty('CastPluginLink', pluginCastLink)
    list.setProperty('ItemGUID', extraData.get('guiid'))
    list.setProperty('id', extraData.get('id'))
    list.setProperty('Video3DFormat', details.get('Video3DFormat'))
        
    return (u, list, folder)

def addContextMenu(details, extraData, folder):
    printDebug("Building Context Menus", level=2)
    commands = []
    watched = extraData.get('watchedurl')
    if watched != None:
        scriptToRun = PLUGINPATH + "/default.py"
        
        pluginCastLink = "XBMC.Container.Update(plugin://plugin.video.mbcon?mode=" + str(_MODE_CAST_LIST) + "&id=" + str(extraData.get('id')) + ")"
        commands.append(( __language__(30100), pluginCastLink))
        
        if extraData.get("playcount") == "0":
            argsToPass = 'markWatched,' + extraData.get('watchedurl')
            commands.append(( __language__(30093), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        else:
            argsToPass = 'markUnwatched,' + extraData.get('watchedurl')
            commands.append(( __language__(30094), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        if extraData.get('favorite') != 'true':
            argsToPass = 'markFavorite,' + extraData.get('favoriteurl')
            commands.append(( __language__(30095), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        else:
            argsToPass = 'unmarkFavorite,' + extraData.get('favoriteurl')
            commands.append(( __language__(30096), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
        argsToPass = 'sortby'
        commands.append(( __language__(30097), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        
        if 'Ascending' in WINDOW.getProperty("currenturl"):
            argsToPass = 'sortorder'
            commands.append(( __language__(30098), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        else:
            argsToPass = 'sortorder'
            commands.append(( __language__(30099), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
            
        argsToPass = 'genrefilter'
        commands.append(( __language__(30040), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
                   
        argsToPass = 'refresh'
        commands.append(( __language__(30042), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        
        argsToPass = 'delete,' + extraData.get('deleteurl')
        commands.append(( __language__(30043), "XBMC.RunScript(" + scriptToRun + ", " + argsToPass + ")"))
        
        if  extraData.get('itemtype') == 'Trailer':
            commands.append(( __language__(30046),"XBMC.RunPlugin(%s)" % CP_ADD_URL % details.get('title')))
            
    return(commands)
    
def getDetailsString():
    detailsString = "EpisodeCount,SeasonCount,Path,Genres,Studios,CumulativeRunTimeTicks"
    if(__settings__.getSetting('includeStreamInfo') == "true"):
        detailsString += ",MediaStreams"
    if(__settings__.getSetting('includePeople') == "true"):
        detailsString += ",People"
    if(__settings__.getSetting('includeOverview') == "true"):
        detailsString += ",Overview"       
    return (detailsString)
    
def displaySections( filter=None ):
    printDebug("== ENTER: displaySections() ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    dirItems = []
    userid = downloadUtils.getUserId()  
    extraData = { 'fanart_image' : '' ,
                  'type'         : "Video" ,
                  'thumb'        : '' }
    
    # Add collections
    detailsString=getDetailsString()
    collections = getCollections(detailsString)
    for collection in collections:
        details = {'title' : collection.get('title', 'Unknown') }
        path = collection['path']
        extraData['mode'] = _MODE_MOVIES
        extraData['thumb'] = collection['thumb']
        extraData['poster'] = collection['poster']
        extraData['fanart_image'] = collection['fanart_image']
        extraData['guiid'] = collection['guiid']
        s_url = 'http://%s%s' % ( collection['address'], path)
        printDebug("addGUIItem:" + str(s_url) + str(details) + str(extraData))
        dirItems.append(addGUIItem(s_url, details, extraData))
        
    #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
    xbmcplugin.addDirectoryItems(pluginhandle, dirItems)
    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)
        
def remove_html_tags( data ):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def PLAY( url, handle ):
    printDebug("== ENTER: PLAY ==")
    url=urllib.unquote(url)
    
    urlParts = url.split(',;')
    xbmc.log("PLAY ACTION URL PARTS : " + str(urlParts))
    server = urlParts[0]
    id = urlParts[1]
    autoResume = 0
    
    if(len(urlParts) > 2):
        autoResume = int(urlParts[2])
        xbmc.log("PLAY ACTION URL AUTO RESUME : " + str(autoResume))
    
    ip,port = server.split(':')
    userid = downloadUtils.getUserId()
    seekTime = 0
    resume = 0
    
    id = urlParts[1]
    jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json", suppress=False, popup=1 )     
    result = json.loads(jsonData)
    
    if(autoResume != 0):
        if(autoResume == -1):
            resume_result = 1
        else:
            resume_result = 0
            seekTime = (autoResume / 1000) / 10000
    else:
        userData = result.get("UserData")
        resume_result = 0
        
        if userData.get("PlaybackPositionTicks") != 0:
            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            seekTime = reasonableTicks / 10000
            displayTime = str(datetime.timedelta(seconds=seekTime))
            display_list = [ "Resume from " + displayTime, "Start from beginning"]
            resumeScreen = xbmcgui.Dialog()
            resume_result = resumeScreen.select('Resume', display_list)
            if resume_result == -1:
                return
    
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    playurl = PlayUtils().getPlayUrl(server, id, result)
    printDebug("Play URL: " + playurl)    
    thumbPath = downloadUtils.getArtwork(result, "Primary")
    listItem = xbmcgui.ListItem(path=playurl, iconImage=thumbPath, thumbnailImage=thumbPath)
    
    setListItemProps(server, id, listItem, result)

    # Can not play virtual items
    if (result.get("LocationType") == "Virtual"):
        xbmcgui.Dialog().ok(__language__(30128), __language__(30129))
        return

    # set the current playing item id
    WINDOW = xbmcgui.Window(10000)
    WINDOW.setProperty("item_id", id)
    
    playlist.add(playurl, listItem)

    xbmc.Player().play(playlist)
    
    #Set a loop to wait for positive confirmation of playback
    count = 0
    while not xbmc.Player().isPlaying():
        printDebug( "Not playing yet...sleep for 1 sec")
        count = count + 1
        if count >= 10:
            return
        else:
            time.sleep(1)
            
    if resume_result == 0:
        jumpBackSec = int(__settings__.getSetting("resumeJumpBack"))
        seekToTime = seekTime - jumpBackSec
        while xbmc.Player().getTime() < (seekToTime - 5):
            xbmc.Player().pause
            xbmc.sleep(100)
            xbmc.Player().seekTime(seekToTime)
            xbmc.sleep(100)
            xbmc.Player().play()
    return

def setListItemProps(server, id, listItem, result):

    # set up item and item info
    thumbID = id
    eppNum = -1
    seasonNum = -1
        
    setArt(listItem,'poster', downloadUtils.getArtwork(result, "Primary"))
    
    listItem.setProperty('IsPlayable', 'true')
    listItem.setProperty('IsFolder', 'false')
    
    # play info       
    details = {
             'title'        : result.get("Name", "Missing Name"),
             'plot'         : result.get("Overview")
             }
             
    if(eppNum > -1):
        details["episode"] = str(eppNum)
        
    if(seasonNum > -1):
        details["season"] = str(seasonNum)
   
    listItem.setInfo( "Video", infoLabels=details )

    return
    
def get_params( paramstring ):
    printDebug("Parameter string: " + paramstring, level=2)
    param={}
    if len(paramstring) >= 2:
            params=paramstring

            if params[0] == "?":
                cleanedparams=params[1:]
            else:
                cleanedparams=params

            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]

            pairsofparams=cleanedparams.split('&')
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                    elif (len(splitparams))==3:
                            param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
    printDebug("MBCon -> Detected parameters: " + str(param), level=2)
    return param

def getCacheValidator (server,url):
    parsedserver,parsedport = server.split(':')
    userid = downloadUtils.getUserId()
    idAndOptions = url.split("ParentId=")
    id = idAndOptions[1].split("&")
    jsonData = downloadUtils.downloadUrl("http://"+server+"/mediabrowser/Users/" + userid + "/Items/" +id[0]+"?format=json", suppress=False, popup=1 )
    result = json.loads(jsonData)
    userData = result.get("UserData")
    printDebug ("RecursiveItemCount: " + str(result.get("RecursiveItemCount")))
    printDebug ("UnplayedItemCount: " + str(userData.get("UnplayedItemCount")))
    printDebug ("PlayedPercentage: " + str(userData.get("PlayedPercentage")))
    
    playedPercentage = 0.0
    if(userData.get("PlayedPercentage") != None):
        playedPercentage = userData.get("PlayedPercentage")
    
    playedTime = "{0:09.6f}".format(playedPercentage)
    playedTime = playedTime.replace(".","-")
    validatorString=""
    if result.get("RecursiveItemCount") != None:
        if int(result.get("RecursiveItemCount"))<=25:
            validatorString='nocache'
        else:
            validatorString = str(result.get("RecursiveItemCount")) + "_" + str(userData.get("UnplayedItemCount")) + "_" + playedTime
        printDebug ("getCacheValidator : " + validatorString)
    return validatorString
    
def getAllMoviesCacheValidator(server,url):
    parsedserver,parsedport = server.split(':')
    userid = downloadUtils.getUserId()
    jsonData = downloadUtils.downloadUrl("http://"+server+"/mediabrowser/Users/" + userid + "/Views?format=json", suppress=False, popup=1 )
    alldata = json.loads(jsonData)
    validatorString = ""
    playedTime = ""
    playedPercentage = 0.0
    
    userData = {}
    result=alldata.get("Items")
    for item in result:
        if item.get("Name")=="Movies":
            userData = item.get("UserData")
            printDebug ("RecursiveItemCount: " + str(item.get("RecursiveItemCount")))
            printDebug ("RecursiveUnplayedCount: " + str(userData.get("UnplayedItemCount")))
            printDebug ("RecursiveUnplayedCount: " + str(userData.get("PlayedPercentage")))

            if(userData.get("PlayedPercentage") != None):
                playedPercentage = userData.get("PlayedPercentage")
            
            playedTime = "{0:09.6f}".format(playedPercentage)
            playedTime = playedTime.replace(".","-")
            
    if item.get("RecursiveItemCount") != None:
        if int(item.get("RecursiveItemCount"))<=25:
            validatorString='nocache'
        else:
            validatorString = "allmovies_" + str(item.get("RecursiveItemCount")) + "_" + str(userData.get("UnplayedItemCount")) + "_" + playedTime
        printDebug ("getAllMoviesCacheValidator : " + validatorString)
    return validatorString    
    
def getCacheValidatorFromData(result):
    result = result.get("Items")
    if(result == None):
        result = []

    itemCount = 0
    unwatchedItemCount = 0
    totalPlayedPercentage = 0
    for item in result:
        userData = item.get("UserData")
        if(userData != None):
            if(item.get("IsFolder") == False):
                itemCount = itemCount + 1
                if userData.get("Played") == False:
                    unwatchedItemCount = unwatchedItemCount + 1
                    itemPossition = userData.get("PlaybackPositionTicks")
                    itemRuntime = item.get("RunTimeTicks")
                    if(itemRuntime != None and itemPossition != None):
                        itemPercent = float(itemPossition) / float(itemRuntime)
                        totalPlayedPercentage = totalPlayedPercentage + itemPercent
                else:
                    totalPlayedPercentage = totalPlayedPercentage + 100
            else:
                itemCount = itemCount + item.get("RecursiveItemCount")
                unwatchedItemCount = unwatchedItemCount + userData.get("UnplayedItemCount")
                PlayedPercentage=userData.get("PlayedPercentage")
                if PlayedPercentage==None:
                    PlayedPercentage=0
                totalPlayedPercentage = totalPlayedPercentage + (item.get("RecursiveItemCount") * PlayedPercentage)
            
    if(itemCount == 0):
        totalPlayedPercentage = 0.0
    else:
        totalPlayedPercentage = totalPlayedPercentage / float(itemCount)
        
    playedTime = "{0:09.6f}".format(totalPlayedPercentage)
    playedTime = playedTime.replace(".","-")
    validatorString = "_" + str(itemCount) + "_" + str(unwatchedItemCount) + "_" + playedTime
    printDebug ("getCacheValidatorFromData : " + validatorString)
    return validatorString
    
def getContent( url ):

    global viewType
    printDebug("== ENTER: getContent ==")
    server=getServerFromURL(url)
    lastbit=url.split('/')[-1]
    printDebug("URL suffix: " + str(lastbit))
    printDebug("server: " + str(server))
    printDebug("URL: " + str(url))    
    validator='nocache' #Don't cache special queries (recently added etc)
    if "Parent" in url:
        validator = "_" + getCacheValidator(server,url)
    elif "&SortOrder=Ascending&IncludeItemTypes=Movie" in url:
        validator = "_" + getAllMoviesCacheValidator(server,url)
        
    # ADD VALIDATOR TO FILENAME TO DETERMINE IF CACHE IS FRESH
    
    m = hashlib.md5()
    m.update(url)
    urlHash = m.hexdigest()
   
    jsonData = ""
    cacheDataPath = __addondir__ + urlHash + validator
    
    if "NextUp" in url and __settings__.getSetting('sortNextUp') == "true":
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TITLE)
    else:
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_NONE)
    result = None
    
    WINDOW = xbmcgui.Window( 10000 )
    force_data_reload = WINDOW.getProperty("force_data_reload")
    WINDOW.setProperty("force_data_reload", "false")
    
    progress = None
    if(__settings__.getSetting('showLoadProgress') == "true"):
        progress = xbmcgui.DialogProgress()
        progress.create(__language__(30121))
        progress.update(0, __language__(30122))    
    
    # if a cached file exists use it
    # if one does not exist then load data from the url
    if(os.path.exists(cacheDataPath)) and validator != 'nocache' and force_data_reload != "true":
        cachedfie = open(cacheDataPath, 'r')
        jsonData = cachedfie.read()
        cachedfie.close()
        printDebug("Data Read From Cache : " + cacheDataPath)
        if(progress != None):
            progress.update(0, __language__(30123))  
        try:
            result = loadJasonData(jsonData)
        except:
            printDebug("Json load failed from cache data")
            result = []
        dataLen = len(result)
        printDebug("Json Load Result : " + str(dataLen))
        if(dataLen == 0):
            result = None
    
    # if there was no cache data for the cache data was not valid then try to load it again
    if(result == None):
        r = glob.glob(__addondir__ + urlHash + "*")
        for i in r:
            os.remove(i)
        printDebug("No Cache Data, download data now")
        if(progress != None):
            progress.update(0, __language__(30124))
        jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1 )
        if(progress != None):
            progress.update(0, __language__(30123))  
        try:
            result = loadJasonData(jsonData)
        except:
            xbmc.log("Json load failed from downloaded data")
            result = []
        dataLen = len(result)
        printDebug("Json Load Result : " + str(dataLen))
        if(dataLen > 0 and validator != 'nocache'):
            cacheValidationString = getCacheValidatorFromData(result)
            printDebug("getCacheValidator : " + validator)
            printDebug("getCacheValidatorFromData : " + cacheValidationString)
            if(validator == cacheValidationString):
                printDebug("Validator String Match, Saving Cache Data")
                cacheDataPath = __addondir__ + urlHash + cacheValidationString
                printDebug("Saving data to cache : " + cacheDataPath)
                cachedfie = open(cacheDataPath, 'w')
                cachedfie.write(jsonData)
                cachedfie.close()
            elif("allmovies" in validator):
                printDebug("All Movies Cache")
                cacheDataPath = __addondir__ + urlHash + validator
                printDebug("Saving data to cache : " + cacheDataPath)
                cachedfie = open(cacheDataPath, 'w')
                cachedfie.write(jsonData)
                cachedfie.close()
    if jsonData == "":
        if(progress != None):
            progress.close()
        return
    
    printDebug("JSON DATA: " + str(result), level=2)
    
    dirItems = processDirectory(url, result, progress)
    xbmcplugin.addDirectoryItems(pluginhandle, dirItems)
    
    if("viewType" in globals()):
        if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW' + viewType) != "":
            xbmc.executebuiltin("Container.SetViewMode(%s)" % int(__settings__.getSetting(xbmc.getSkinDir()+ '_VIEW' + viewType)))
            
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
    
    if(progress != None):
        progress.update(100, __language__(30125))
        progress.close()
    
    return

def loadJasonData(jsonData):
    return json.loads(jsonData)
    
def processDirectory(url, results, progress):
    global viewType
    cast=['None']
    printDebug("== ENTER: processDirectory ==")
    parsed = urlparse(url)
    parsedserver,parsedport=parsed.netloc.split(':')
    userid = downloadUtils.getUserId()
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, 'movies')

    server = getServerFromURL(url)
    setWindowHeading(url)
    
    detailsString = "Path,Genres,Studios,CumulativeRunTimeTicks"
    if(__settings__.getSetting('includeStreamInfo') == "true"):
        detailsString += ",MediaStreams"
    if(__settings__.getSetting('includePeople') == "true"):
        detailsString += ",People"
    if(__settings__.getSetting('includeOverview') == "true"):
        detailsString += ",Overview"            
    
    dirItems = []
    result = results.get("Items")
    if(result == None):
        result = []
    if len(result) == 1 and __settings__.getSetting('autoEnterSingle') == "true":
        if result[0].get("Type") == "Season":
            jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + result[0].get("Id") + '&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy=SortName&format=json', suppress=False, popup=1 )
            results = json.loads(jsonData)
            result=results.get("Items")
    item_count = len(result)
    current_item = 1;
        
    for item in result:
    
        if(progress != None):
            percentDone = (float(current_item) / float(item_count)) * 100
            progress.update(int(percentDone), __language__(30126) + str(current_item))
            current_item = current_item + 1
        
        if(item.get("Name") != None):
            tempTitle = item.get("Name").encode('utf-8')
        else:
            tempTitle = "Missing Title"
            
        id = str(item.get("Id")).encode('utf-8')
        guiid = id
        isFolder = item.get("IsFolder")
       
        item_type = str(item.get("Type")).encode('utf-8')
              
        tempEpisode = ""
        if (item.get("IndexNumber") != None):
            episodeNum = item.get("IndexNumber")
            if episodeNum < 10:
                tempEpisode = "0" + str(episodeNum)
            else:
                tempEpisode = str(episodeNum)
                
        tempSeason = ""
        if (str(item.get("ParentIndexNumber")) != None):
            tempSeason = str(item.get("ParentIndexNumber"))
            if item.get("ParentIndexNumber") < 10:
                tempSeason = "0" + tempSeason
      
        viewType=""
        if item.get("Type") == "Movie":
            xbmcplugin.setContent(pluginhandle, 'movies')
            viewType="_MOVIES"
        elif item.get("Type") == "BoxSet":
            xbmcplugin.setContent(pluginhandle, 'movies')
            viewType="_BOXSETS"
        elif item.get("Type") == "Trailer":
            xbmcplugin.setContent(pluginhandle, 'movies')
            viewType="_TRAILERS"            
        elif item.get("Type") == "Series":
            xbmcplugin.setContent(pluginhandle, 'tvshows')
            viewType="_SERIES"
        elif item.get("Type") == "Season":
            xbmcplugin.setContent(pluginhandle, 'seasons')
            viewType="_SEASONS"
            guiid = item.get("SeriesId")
        elif item.get("Type") == "Episode":
            prefix=''
            if __settings__.getSetting('addSeasonNumber') == 'true':
                prefix = "S" + str(tempSeason)
                if __settings__.getSetting('addEpisodeNumber') == 'true':
                    prefix = prefix + "E"
                #prefix = str(tempEpisode)
            if __settings__.getSetting('addEpisodeNumber') == 'true':
                prefix = prefix + str(tempEpisode)
            if prefix != '':
                tempTitle = prefix + ' - ' + tempTitle
            xbmcplugin.setContent(pluginhandle, 'episodes')
            viewType="_EPISODES"
            guiid = item.get("SeriesId")
        elif item.get("Type") == "MusicArtist":
            xbmcplugin.setContent(pluginhandle, 'songs')
            viewType='_MUSICARTISTS'
        elif item.get("Type") == "MusicAlbum":
            xbmcplugin.setContent(pluginhandle, 'songs')
            viewType='_MUSICTALBUMS'
        elif item.get("Type") == "Audio":
            xbmcplugin.setContent(pluginhandle, 'songs')
            viewType='_MUSICTRACKS'
        
        if(item.get("PremiereDate") != None):
            premieredatelist = (item.get("PremiereDate")).split("T")
            premieredate = premieredatelist[0]
        else:
            premieredate = ""
        
        # add the premiered date for Upcoming TV    
        if item.get("LocationType") == "Virtual":
            airtime = item.get("AirTime")
            tempTitle = tempTitle + ' - ' + str(premieredate) + ' - ' + str(airtime)     

        #Add show name to special TV collections RAL, NextUp etc
        WINDOW = xbmcgui.Window( 10000 )
        if (WINDOW.getProperty("addshowname") == "true" and item.get("SeriesName") != None):
            tempTitle=item.get("SeriesName").encode('utf-8') + " - " + tempTitle
        else:
            tempTitle=tempTitle

        # Process MediaStreams
        channels = ''
        videocodec = ''
        audiocodec = ''
        height = ''
        width = ''
        aspectratio = '1:1'
        aspectfloat = 1.85
        mediaStreams = item.get("MediaStreams")
        if(mediaStreams != None):
            for mediaStream in mediaStreams:
                if(mediaStream.get("Type") == "Video"):
                    videocodec = mediaStream.get("Codec")
                    height = str(mediaStream.get("Height"))
                    width = str(mediaStream.get("Width"))
                    aspectratio = mediaStream.get("AspectRatio")
                    if aspectratio != None and len(aspectratio) >= 3:
                        try:
                            aspectwidth,aspectheight = aspectratio.split(':')
                            aspectfloat = float(aspectwidth) / float(aspectheight)
                        except:
                            aspectfloat = 1.85
                if(mediaStream.get("Type") == "Audio"):
                    audiocodec = mediaStream.get("Codec")
                    channels = mediaStream.get("Channels")
                
        # Process People
        director=''
        writer=''
        cast=[]
        people = item.get("People")
        if(people != None):
            for person in people:
                if(person.get("Type") == "Director"):
                    director = director + person.get("Name") + ' ' 
                if(person.get("Type") == "Writing"):
                    writer = person.get("Name")
                if(person.get("Type") == "Writer"):
                    writer = person.get("Name")                 
                if(person.get("Type") == "Actor"):
                    Name = person.get("Name")
                    Role = person.get("Role")
                    if Role == None:
                        Role = ''
                    cast.append(Name)

        # Process Studios
        studio = ""
        studios = item.get("Studios")
        if(studios != None):
            for studio_string in studios:
                if studio=="": #Just take the first one
                    temp=studio_string.get("Name")
                    studio=temp.encode('utf-8')
        # Process Genres
        genre = ""
        genres = item.get("Genres")
        if(genres != None and genres != []):
            for genre_string in genres:
                if genre == "": #Just take the first genre
                    genre = genre_string
                elif genre_string != None:
                    genre = genre + " / " + genre_string
                
        # Process UserData
        userData = item.get("UserData")
        PlaybackPositionTicks = '100'
        overlay = "0"
        favorite = "false"
        seekTime = 0
        if(userData != None):
            if userData.get("Played") != True:
                overlay = "7"
                watched = "true"
            else:
                overlay = "6"
                watched = "false"
            if userData.get("IsFavorite") == True:
                overlay = "5"
                favorite = "true"
            else:
                favorite = "false"
            if userData.get("PlaybackPositionTicks") != None:
                PlaybackPositionTicks = str(userData.get("PlaybackPositionTicks"))
                reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
                seekTime = reasonableTicks / 10000
        
        playCount = 0
        if(userData != None and userData.get("Played") == True):
            playCount = 1
        # Populate the details list
        details={'title'        : tempTitle,
                 'plot'         : item.get("Overview"),
                 'episode'      : tempEpisode,
                 #'watched'      : watched,
                 'Overlay'      : overlay,
                 'playcount'    : str(playCount),
                 #'aired'       : episode.get('originallyAvailableAt','') ,
                 'TVShowTitle'  :  item.get("SeriesName"),
                 'season'       : tempSeason,
                 'Video3DFormat' : item.get("Video3DFormat"),
                 }
                 
        try:
            tempDuration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
            RunTimeTicks = str(item.get("RunTimeTicks", "0"))
        except TypeError:
            try:
                tempDuration = str(int(item.get("CumulativeRunTimeTicks"))/(10000000*60))
                RunTimeTicks = str(item.get("CumulativeRunTimeTicks"))
            except TypeError:
                tempDuration = "0"
                RunTimeTicks = "0"
        TotalSeasons     = 0 if item.get("ChildCount")==None else item.get("ChildCount")
        TotalEpisodes    = 0 if item.get("RecursiveItemCount")==None else item.get("RecursiveItemCount")
        WatchedEpisodes  = 0 if userData.get("UnplayedItemCount")==None else TotalEpisodes-userData.get("UnplayedItemCount")
        UnWatchedEpisodes = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")
        NumEpisodes      = TotalEpisodes
        # Populate the extraData list
        extraData={'thumb'        : downloadUtils.getArtwork(item, "Primary") ,
                   'fanart_image' : downloadUtils.getArtwork(item, "Backdrop") ,
                   'poster'       : downloadUtils.getArtwork(item, "poster") , 
                   'banner'       : downloadUtils.getArtwork(item, "Banner") ,
                   'clearlogo'    : downloadUtils.getArtwork(item, "Logo") ,
                   'discart'      : downloadUtils.getArtwork(item, "Disc") ,
                   'clearart'     : downloadUtils.getArtwork(item, "Art") ,
                   'landscape'    : downloadUtils.getArtwork(item, "Thumb") ,                
                   'id'           : id ,
                   'guiid'        : guiid ,
                   'mpaa'         : item.get("OfficialRating"),
                   'rating'       : item.get("CommunityRating"),
                   'criticrating' : item.get("CriticRating"), 
                   'year'         : item.get("ProductionYear"),
                   'locationtype' : item.get("LocationType"),
                   'premieredate' : premieredate,
                   'studio'       : studio,
                   'genre'        : genre,
                   'playcount'    : str(playCount),
                   'director'     : director,
                   'writer'       : writer,
                   'channels'     : channels,
                   'videocodec'   : videocodec,
                   'aspectratio'  : str(aspectfloat),
                   'audiocodec'   : audiocodec,
                   'height'       : height,
                   'width'        : width,
                   'cast'         : cast,
                   'favorite'     : favorite,
                   'watchedurl'   : 'http://' + server + '/mediabrowser/Users/'+ userid + '/PlayedItems/' + id,
                   'favoriteurl'  : 'http://' + server + '/mediabrowser/Users/'+ userid + '/FavoriteItems/' + id,
                   'deleteurl'    : 'http://' + server + '/mediabrowser/Items/' + id,                   
                   'parenturl'    : url,
                   'resumetime'   : str(seekTime),
                   'totaltime'    : tempDuration,
                   'duration'     : tempDuration,
                   'RecursiveItemCount' : item.get("RecursiveItemCount"),
                   'RecursiveUnplayedItemCount' : userData.get("UnplayedItemCount"),
                   'TotalSeasons' : str(TotalSeasons),
                   'TotalEpisodes': str(TotalEpisodes),
                   'WatchedEpisodes': str(WatchedEpisodes),
                   'UnWatchedEpisodes': str(UnWatchedEpisodes),
                   'NumEpisodes'  : str(NumEpisodes),
                   'itemtype'     : item_type}

        if extraData['thumb'] == '':
            extraData['thumb'] = extraData['fanart_image']

        extraData['mode'] = _MODE_GETCONTENT
        
        if isFolder == True:
            SortByTemp = __settings__.getSetting('sortby')
            if SortByTemp == '' and not (item_type == 'Series' or item_type == 'Season' or item_type == 'BoxSet' or item_type == 'MusicAlbum' or item_type == 'MusicArtist'):
                SortByTemp = 'SortName'
            if item_type=='Series' and __settings__.getSetting('flattenSeasons')=='true':
                u = 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&IncludeItemTypes=Episode&Recursive=true&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy=SortName'+'&format=json'
            else:
                u = 'http://' + server + '/mediabrowser/Users/'+ userid + '/items?ParentId=' +id +'&IsVirtualUnAired=false&IsMissing=false&Fields=' + detailsString + '&SortBy='+SortByTemp+'&format=json'
            if (item.get("RecursiveItemCount") != 0):
                dirItems.append(addGUIItem(u, details, extraData))
        else:
            u = server+',;'+id
            dirItems.append(addGUIItem(u, details, extraData, folder=False))

    return dirItems
    
def getServerFromURL( url ):
    '''
    Simply split the URL up and get the server portion, sans port
    @ input: url, woth or without protocol
    @ return: the URL server
    '''
    if url[0:4] == "http":
        return url.split('/')[2]
    else:
        return url.split('/')[0]

def getLinkURL( url, pathData, server ):
    '''
        Investigate the passed URL and determine what is required to
        turn it into a usable URL
        @ input: url, XML data and PM server address
        @ return: Usable http URL
    '''
    printDebug("== ENTER: getLinkURL ==")
    path=pathData.get('key','')
    printDebug("Path is " + path)

    if path == '':
        printDebug("Empty Path")
        return

    #If key starts with http, then return it
    if path[0:4] == "http":
        printDebug("Detected http link")
        return path

    #If key starts with a / then prefix with server address
    elif path[0] == '/':
        printDebug("Detected base path link")
        return 'http://%s%s' % ( server, path )

    elif path[0:5] == "rtmp:":
        printDebug("Detected  link")
        return path

    #Any thing else is assumed to be a relative path and is built on existing url
    else:
        printDebug("Detected relative link")
        return "%s/%s" % ( url, path )

    return url

def setArt (list, name, path):
    if name=='thumb' or name=='fanart_image' or name=='small_poster' or name == "medium_landscape" or name=='medium_poster' or name=='small_fanartimage' or name=='medium_fanartimage':
        list.setProperty(name, path)
    elif xbmcVersionNum >= 13:
        list.setArt({name:path})
    return list
        
def getXbmcVersion():
    version = 0.0
    jsonData = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }') 
    
    result = json.loads(jsonData)
    
    try:
        result = result.get("result")
        versionData = result.get("version")
        version = float(str(versionData.get("major")) + "." + str(versionData.get("minor")))
        printDebug("Version : " + str(version) + " - " + str(versionData), level=0)
    except:
        version = 0.0
        printDebug("Version Error : RAW Version Data : " + str(result), level=0)

    return version        
    
def setWindowHeading(url) :
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("addshowname", "false")
    WINDOW.setProperty("currenturl", url)
    WINDOW.setProperty("currentpluginhandle", str(pluginhandle))
    if 'ParentId' in url:
        dirUrl = url.replace('items?ParentId=','Items/')
        splitUrl = dirUrl.split('&')
        dirUrl = splitUrl[0] + '?format=json'
        jsonData = downloadUtils.downloadUrl(dirUrl)
        result = json.loads(jsonData)
        for name in result:
            title = name
        WINDOW.setProperty("heading", title)
    elif 'IncludeItemTypes=Episode' in url:
        WINDOW.setProperty("addshowname", "true")

def getCastList(pluginName, handle, params):

    printDebug ("MBCon Returning Cast List")
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port
    userid = downloadUtils.getUserId()
    seekTime = 0
    resume = 0
    
    # get the cast list for an item
    jsonData = downloadUtils.downloadUrl("http://" + server + "/mediabrowser/Users/" + userid + "/Items/" + params.get("id") + "?format=json", suppress=False, popup=1 )    
    printDebug("CastList(Items) jsonData: " + jsonData, 2)
    result = json.loads(jsonData)

    people = result.get("People")
    
    if(people == None):
        return
    
    listItems = []

    for person in people:

        displayName = person.get("Name")
        if(person.get("Role") != None):
            displayName = displayName + " (" + person.get("Role") + ")"
            
        tag = person.get("PrimaryImageTag")
        id = person.get("Id")
        
        baseName = person.get("Name")
        #urllib.quote(baseName)
        baseName = baseName.replace(" ", "+")
        baseName = baseName.replace("&", "_")
        baseName = baseName.replace("?", "_")
        baseName = baseName.replace("=", "_")
            
        if(tag != None):
            thumbPath = downloadUtils.imageUrl(id, "Primary", 0, 400, 400)
            item = xbmcgui.ListItem(label=displayName, iconImage=thumbPath, thumbnailImage=thumbPath)
        else:
            item = xbmcgui.ListItem(label=displayName)
            
        actionUrl = "plugin://plugin.video.mbcon?mode=" + str(_MODE_PERSON_DETAILS) +"&name=" + baseName
        
        item.setProperty('IsPlayable', 'false')
        item.setProperty('IsFolder', 'false')
        
        commands = []
        detailsString = getDetailsString()
        url = "http://" + host + ":" + port + "/mediabrowser/Users/" + userid + "/Items/?Recursive=True&Person=PERSON_NAME&Fields=" + detailsString + "&format=json"
        url = urllib.quote(url)
        url = url.replace("PERSON_NAME", baseName)
        pluginCastLink = "XBMC.Container.Update(plugin://plugin.video.mbcon?mode=" + str(_MODE_GETCONTENT) + "&url=" + url + ")"
        commands.append(( "Show Other Library Items", pluginCastLink))
        item.addContextMenuItems( commands, g_contextReplace )
        
        itemTupple = (actionUrl, item, False)
        listItems.append(itemTupple)
        
        
    #listItems.sort()
    xbmcplugin.addDirectoryItems(handle, listItems)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

def showItemInfo(pluginName, handle, params):    
    printDebug("showItemInfo Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    
    infoPage = ItemInfo("ItemInfo.xml", __cwd__, "default", "720p")
    
    infoPage.setId(params.get("id"))
    infoPage.doModal()
    
    del infoPage
    
def showSearch(pluginName, handle, params):
    printDebug("showSearch Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
       
    searchDialog = SearchDialog("SearchDialog.xml", __cwd__, "default", "720p")
    searchDialog.doModal()
    del searchDialog
    
    #items = DisplayItems("DisplayItems.xml", __cwd__, "default", "720p")
    #items.doModal()
    #del items    
    
def showPersonInfo(pluginName, handle, params):
    printDebug("showPersonInfo Called" + str(params))
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)

    infoPage = PersonInfo("PersonInfo.xml", __cwd__, "default", "720p")
    
    infoPage.setPersonName(params.get("name"))
    infoPage.doModal()
    
    if(infoPage.showMovies == True):
        xbmc.log("RUNNING_PLUGIN: " + infoPage.pluginCastLink)
        xbmc.executebuiltin(infoPage.pluginCastLink)    
    
    del infoPage
        
def getWigetContent(pluginName, handle, params):
    printDebug("getWigetContent Called" + str(params))
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port    
    
    collectionType = params.get("CollectionType")
    type = params.get("type")
    parentId = params.get("ParentId")
    
    if(type == None):
        printDebug("getWigetContent No Type")
        return
    
    userid = downloadUtils.getUserId()
    
    if(type == "recent"):
        itemsUrl = "http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId + "&Limit=10&SortBy=DateCreated&Fields=Path,Overview&SortOrder=Descending&Filters=IsNotFolder&IncludeItemTypes=Movie,Episode,Trailer,Musicvideo,Video&CollapseBoxSetItems=false&IsVirtualUnaired=false&Recursive=true&IsMissing=False&format=json"
    elif(type == "active"):
        itemsUrl = "http://" + server + "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId + "&Limit=10&SortBy=DatePlayed&Fields=Path,Overview&SortOrder=Descending&Filters=IsResumable,IsNotFolder&IncludeItemTypes=Movie,Episode,Trailer,Musicvideo,Video&CollapseBoxSetItems=false&IsVirtualUnaired=false&Recursive=true&IsMissing=False&format=json"
        
    printDebug("WIDGET_DATE_URL: " + itemsUrl, 2)
    
    # get the recent items
    jsonData = downloadUtils.downloadUrl(itemsUrl, suppress=False, popup=1 )
    printDebug("Recent(Items) jsonData: " + jsonData, 2)
    result = json.loads(jsonData)
    
    result = result.get("Items")
    if(result == None):
        result = []   

    itemCount = 1
    listItems = []
    for item in result:
        item_id = item.get("Id")

        image_id = item_id
        if item.get("Type") == "Episode":
            image_id = item.get("SeriesId")
        
        #image = downloadUtils.getArtwork(item, "Primary")
        image = downloadUtils.imageUrl(image_id, "Primary", 0, 400, 400)
        fanart = downloadUtils.getArtwork(item, "Backdrop")
        
        Duration = str(int(item.get("RunTimeTicks", "0"))/(10000000*60))
        
        name = item.get("Name")
        printDebug("WIDGET_DATE_NAME: " + name, 2)
        
        seriesName = ''
        if(item.get("SeriesName") != None):
            seriesName = item.get("SeriesName").encode('utf-8')   

            eppNumber = "X"
            tempEpisodeNumber = "00"
            if(item.get("IndexNumber") != None):
                eppNumber = item.get("IndexNumber")
                if eppNumber < 10:
                  tempEpisodeNumber = "0" + str(eppNumber)
                else:
                  tempEpisodeNumber = str(eppNumber)     

            seasonNumber = item.get("ParentIndexNumber")
            if seasonNumber < 10:
              tempSeasonNumber = "0" + str(seasonNumber)
            else:
              tempSeasonNumber = str(seasonNumber)                  
                  
            name =  tempSeasonNumber + "x" + tempEpisodeNumber + "-" + name
        
        list_item = xbmcgui.ListItem(label=name, iconImage=image, thumbnailImage=image)
        list_item.setInfo( type="Video", infoLabels={ "year":item.get("ProductionYear"), "duration":str(Duration), "plot":item.get("Overview"), "tvshowtitle":str(seriesName), "premiered":item.get("PremiereDate"), "rating":item.get("CommunityRating") } )
        list_item.setProperty('fanart_image',fanart)
        
        # add count
        list_item.setProperty("item_index", str(itemCount))
        itemCount = itemCount + 1

        # add progress percent
        
        userData = item.get("UserData")
        PlaybackPositionTicks = '100'
        overlay = "0"
        favorite = "false"
        seekTime = 0
        if(userData != None):
            playBackTicks = float(userData.get("PlaybackPositionTicks"))
            if(playBackTicks != None and playBackTicks > 0):
                runTimeTicks = float(item.get("RunTimeTicks", "0"))
                if(runTimeTicks > 0):
                    percentage = int((playBackTicks / runTimeTicks) * 100.0)
                    cappedPercentage = percentage - (percentage % 10)
                    if(cappedPercentage == 0):
                        cappedPercentage = 10
                    if(cappedPercentage == 100):
                        cappedPercentage = 90
                    list_item.setProperty("complete_percentage", str(cappedPercentage))
                
        selectAction = __settings__.getSetting('selectAction')
        if(selectAction == "1"):
            playUrl = "plugin://plugin.video.mbcon/?id=" + item_id + '&mode=' + str(_MODE_ITEM_DETAILS)
        else:
            url =  server + ',;' + item_id
            playUrl = "plugin://plugin.video.mbcon/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
        
        itemTupple = (playUrl, list_item, False)
        listItems.append(itemTupple)
    
    xbmcplugin.addDirectoryItems(handle, listItems)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    
def showParentContent(pluginName, handle, params):
    printDebug("showParentContent Called" + str(params), 2)
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    server = host + ":" + port
    
    parentId = params.get("ParentId")
    name = params.get("Name")
    detailsString = getDetailsString()
    userid = downloadUtils.getUserId()
    
    contentUrl = (
        "http://" + server +
        "/mediabrowser/Users/" + userid + "/items?ParentId=" + parentId +
        "&IsVirtualUnaired=false" +
        "&IsMissing=False" +
        "&Fields=" + detailsString +
        "&SortOrder=" + __settings__.getSetting('sortorderfor' + urllib.quote(name)) +
        "&SortBy=" + __settings__.getSetting('sortbyfor' + urllib.quote(name)) +
        "&Genres=&format=json")
    
    printDebug("showParentContent Content Url : " + str(contentUrl), 2)
    
    getContent(contentUrl)
    
def showViewList(url, pluginhandle):
    viewCats=['Movies', 'BoxSets', 'Trailers', 'Series', 'Seasons', 'Episodes', 'Music Artists', 'Music Albums', 'Music Videos', 'Music Tracks']
    viewTypes=['_MOVIES', '_BOXSETS', '_TRAILERS', '_SERIES', '_SEASONS', '_EPISODES', '_MUSICARTISTS', '_MUSICALBUMS', '_MUSICVIDEOS', '_MUSICTRACKS']
    
    if "SETVIEWS" in url:
        for viewCat in viewCats:
            xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.mbcon/?url=_SHOWVIEWS' + viewTypes[viewCats.index(viewCat)] + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(viewCat, ''), isFolder=True)
    elif "_SETVIEW_" in url:
        category=url.split('_')[2]
        viewNum=url.split('_')[3]
        __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' +category,viewNum)
        xbmc.executebuiltin("Container.Refresh")    
    else:
        
        skin_view_file = os.path.join(xbmc.translatePath('special://skin'), "views.xml")
        try:
            tree = etree.parse(skin_view_file)
        except:
            xbmcgui.Dialog().ok(__language__(30135), __language__(30150))            
            sys.exit()
        root = tree.getroot()
        xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.mbcon?url=_SETVIEW_'+ url.split('_')[2] + '_' + '' + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem('Clear Settings', 'test'))
        for view in root.iter('view'):
            if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW_'+ url.split('_')[2]) == view.attrib['value']:
                name=view.attrib['id'] + " (Active)"
            else:
                name=view.attrib['id']
            xbmcplugin.addDirectoryItem(pluginhandle, 'plugin://plugin.video.mbcon?url=_SETVIEW_'+ url.split('_')[2] + '_' + view.attrib['value'] + '&mode=' + str(_MODE_SETVIEWS), xbmcgui.ListItem(name, 'test'))
            
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
    
def checkService():

    timeStamp = xbmcgui.Window(10000).getProperty("XBMB3C_Service_Timestamp")
    loops = 0
    while(timeStamp == ""):
        timeStamp = xbmcgui.Window(10000).getProperty("XBMB3C_Service_Timestamp")
        loops = loops + 1
        if(loops == 40):
            printDebug("MBCon Service Not Running, no time stamp, exiting", 0)
            xbmcgui.Dialog().ok(__language__(30135), __language__(30136), __language__(30137))
            sys.exit()
        xbmc.sleep(200)
        
    printDebug ("MBCon Service Timestamp: " + timeStamp)
    printDebug ("MBCon Current Timestamp: " + str(int(time.time())))
    
    if((int(timeStamp) + 240) < int(time.time())):
        printDebug("MBCon Service Not Running, time stamp to old, exiting", 0)
        xbmcgui.Dialog().ok(__language__(30135), __language__(30136), __language__(30137))
        sys.exit()
        
def checkServer():
    printDebug ("MBCon checkServer Called")
    
    port = __settings__.getSetting('port')
    host = __settings__.getSetting('ipaddress')
    
    if(len(host) != 0 and host != "<none>"):
        printDebug ("MBCon server already set")
        return
    
    serverInfo = getServerDetails()
    
    if(serverInfo == None):
        printDebug ("MBCon getServerDetails failed")
        return
        
    index = serverInfo.find(":")
    
    if(index <= 0):
        printDebug ("MBCon getServerDetails data not correct : " + serverInfo)
        return
    
    server_address = serverInfo[:index]
    server_port = serverInfo[index+1:]
    printDebug ("MBCon detected server info " + server_address + " : " + server_port)
    
    xbmcgui.Dialog().ok(__language__(30167), __language__(30168), __language__(30169) + server_address, __language__(30030) + server_port)

    # get a list of users
    printDebug ("Getting user list")
    jsonData = None
    try:
        jsonData = downloadUtils.downloadUrl(server_address + ":" + server_port + "/mediabrowser/Users?format=json")
    except Exception, msg:
        error = "Get User unable to connect to " + server_address + ":" + server_port + " : " + str(msg)
        xbmc.log (error)
        return ""
    
    if(jsonData == False):
        return

    printDebug("jsonData : " + str(jsonData), level=2)
    result = json.loads(jsonData)
    
    names = []
    userList = []
    for user in result:
        config = user.get("Configuration")
        if(config != None):
            if(config.get("IsHidden") == False):
                name = user.get("Name")
                userList.append(name)
                if(user.get("HasPassword") == True):
                    name = name + " (Secure)"
                names.append(name)

    printDebug ("User List : " + str(names))
    printDebug ("User List : " + str(userList))
    return_value = xbmcgui.Dialog().select(__language__(30200), names)
    
    if(return_value > -1):
        selected_user = userList[return_value]
        printDebug("Setting Selected User : " + selected_user)
        if __settings__.getSetting("port") != server_port:
            __settings__.setSetting("port", server_port)
        if __settings__.getSetting("ipaddress") != server_address:        
            __settings__.setSetting("ipaddress", server_address)        
        if __settings__.getSetting("username") != selected_user:          
            __settings__.setSetting("username", selected_user)

###########################################################################  
##Start of Main
###########################################################################
if(logLevel == 2):
    xbmcgui.Dialog().ok(__language__(30132), __language__(30133), __language__(30134))

printDebug( "MBCon -> Script argument date " + str(sys.argv))
xbmcVersionNum = getXbmcVersion()
try:
    params=get_params(sys.argv[2])
except:
    params={}
printDebug( "MBCon -> Script params is " + str(params))
    #Check to see if XBMC is playing - we don't want to do anything if so
#if xbmc.Player().isPlaying():
#    printDebug ('Already Playing! Exiting...')
#    sys.exit()
#Now try and assign some data to them
param_url=params.get('url',None)

if param_url and ( param_url.startswith('http') or param_url.startswith('file') ):
    param_url = urllib.unquote(param_url)

param_name = urllib.unquote_plus(params.get('name',""))
mode = int(params.get('mode',-1))
param_transcodeOverride = int(params.get('transcode',0))
param_identifier = params.get('identifier',None)
param_indirect = params.get('indirect',None)
force = params.get('force')
WINDOW = xbmcgui.Window( 10000 )
WINDOW.setProperty("addshowname","false")

if str(sys.argv[1]) == "skin":
     skin()
elif sys.argv[1] == "check_server":
     checkServer()
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
elif sys.argv[1] == "markWatched":
    url=sys.argv[2]
    markWatched(url)
elif sys.argv[1] == "markUnwatched":
    url=sys.argv[2]
    markUnwatched(url)
elif sys.argv[1] == "markFavorite":
    url=sys.argv[2]
    markFavorite(url)
elif sys.argv[1] == "unmarkFavorite":
    url=sys.argv[2]
    unmarkFavorite(url)    
elif sys.argv[1] == "setting":
    __settings__.openSettings()
    WINDOW = xbmcgui.getCurrentWindowId()
    if WINDOW == 10000:
        printDebug("Currently in home - refreshing to allow new settings to be taken")
        xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
elif sys.argv[1] == "delete":
    url=sys.argv[2]
    delete(url)
elif sys.argv[1] == "refresh":
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty("force_data_reload", "true")    
    xbmc.executebuiltin("Container.Refresh")    
elif sys.argv[1] == "sortby":
    sortby()
elif sys.argv[1] == "sortorder":
    sortorder()
elif sys.argv[1] == "genrefilter":
    genrefilter()
elif mode == _MODE_CAST_LIST:
    getCastList(sys.argv[0], int(sys.argv[1]), params)
elif mode == _MODE_PERSON_DETAILS:    
    showPersonInfo(sys.argv[0], int(sys.argv[1]), params)    
elif mode == _MODE_WIDGET_CONTENT:
    getWigetContent(sys.argv[0], int(sys.argv[1]), params)
elif mode == _MODE_ITEM_DETAILS:
    showItemInfo(sys.argv[0], int(sys.argv[1]), params)    
elif mode == _MODE_SHOW_SEARCH:
    showSearch(sys.argv[0], int(sys.argv[1]), params)        
elif mode == _MODE_SHOW_PARENT_CONTENT:
    checkService()
    checkServer()
    pluginhandle = int(sys.argv[1])
    showParentContent(sys.argv[0], int(sys.argv[1]), params)
else:
    
    checkService()
    checkServer()
    
    pluginhandle = int(sys.argv[1])

    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.clearProperty("heading")
    #mode=_MODE_BASICPLAY

    printDebug("MBCon -> Mode: "+str(mode))
    printDebug("MBCon -> URL: "+str(param_url))
    printDebug("MBCon -> Name: "+str(param_name))
    printDebug("MBCon -> identifier: " + str(param_identifier))

    #Run a function based on the mode variable that was passed in the URL
    if ( mode == None or mode == _MODE_SHOW_SECTIONS or param_url == None or len(param_url) < 1 ):
        displaySections()

    elif mode == _MODE_GETCONTENT:
        getContent(param_url)

    elif mode == _MODE_BASICPLAY:
        PLAY(param_url, pluginhandle)
    elif mode == _MODE_SETVIEWS:
        showViewList(param_url, pluginhandle)

WINDOW = xbmcgui.Window( 10000 )
WINDOW.clearProperty("MB3.Background.Item.FanArt")
xbmc.log ("===== MBCon STOP =====")

if(ProfileCode):
    pr.disable()
    ps = pstats.Stats(pr)
    
    fileTimeStamp = time.strftime("%Y-%m-%d %H-%M-%S")
    tabFileName = __addondir__ + "profile_(" + fileTimeStamp + ").tab"
    f = open(tabFileName, 'wb')
    f.write("NumbCalls\tTotalTime\tCumulativeTime\tFunctionName\tFileName\r\n")
    for (key, value) in ps.stats.items():
        (filename, count, func_name) = key
        (ccalls, ncalls, total_time, cumulative_time, callers) = value
        try:
            f.write(str(ncalls) + "\t" + "{:10.4f}".format(total_time) + "\t" + "{:10.4f}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
        except ValueError:
            f.write(str(ncalls) + "\t" + "{0}".format(total_time) + "\t" + "{0}".format(cumulative_time) + "\t" + func_name + "\t" + filename + "\r\n")
    f.close()
    
#clear done and exit.
sys.modules.clear()    


