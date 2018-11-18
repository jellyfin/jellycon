# Gnu General Public License - see LICENSE.TXT

import json
from collections import defaultdict
import threading
import hashlib
import os
import cPickle
import copy
import urllib

from downloadutils import DownloadUtils
from simple_logging import SimpleLogging
from item_functions import extract_item_info
from .kodi_utils import HomeWindow

import xbmc
import xbmcaddon

log = SimpleLogging(__name__)

class DataManager():

    addon_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    def __init__(self, *args):
        log.debug("DataManager __init__")

    def loadJasonData(self, jsonData):
        return json.loads(jsonData, object_hook=lambda d: defaultdict(lambda: None, d))

    def GetContent(self, url):
        jsonData = DownloadUtils().downloadUrl(url)
        result = self.loadJasonData(jsonData)
        return result

    def get_items(self, url, gui_options, use_cache=False):

        home_window = HomeWindow()
        home_window.setProperty("last_content_url", url)

        user_id = DownloadUtils().getUserId()

        m = hashlib.md5()
        m.update(user_id + "|" + url)
        url_hash = m.hexdigest()
        cache_file = os.path.join(self.addon_dir, "cache_" + url_hash + ".pickle")

        #changed_url = url + "&MinDateLastSavedForUser=" + urllib.unquote("2019-09-16T13:45:30")
        #results = self.GetContent(changed_url)
        #log.debug("DataManager Changes Since Date : {0}", results)


        item_list = []
        baseline_name = None
        cache_thread = CacheManagerThread()
        cache_thread.cache_file = cache_file
        cache_thread.cache_url = url
        cache_thread.gui_options = gui_options
        cache_thread.dataManager = self

        home_window.setProperty(cache_file, "true")

        clear_cache = home_window.getProperty(url)
        if clear_cache and os.path.isfile(cache_file):
            log.debug("Clearing cache data and loading new data")
            home_window.clearProperty(url)
            os.remove(cache_file)

        if os.path.isfile(cache_file) and use_cache:
            log.debug("Loading url data from cached pickle data")

            with open(cache_file, 'rb') as handle:
                item_list = cPickle.load(handle)

            cache_thread.cached_data = item_list

        else:
            log.debug("Loading url data from server")

            results = self.GetContent(url)

            if results is None:
                results = []

            if isinstance(results, dict) and results.get("Items") is not None:
                baseline_name = results.get("BaselineItemName")
                results = results.get("Items", [])
            elif isinstance(results, list) and len(results) > 0 and results[0].get("Items") is not None:
                baseline_name = results[0].get("BaselineItemName")
                results = results[0].get("Items")

            for item in results:
                item_data = extract_item_info(item, gui_options)
                item_data.baseline_itemname = baseline_name
                item_list.append(item_data)

            cache_thread.fresh_data = item_list#copy.deepcopy(item_list)

        if use_cache:
            cache_thread.start()

        return cache_file, item_list


class CacheManagerThread(threading.Thread):
    cached_data = None
    fresh_data = None
    cache_file = None
    cache_url = None
    gui_options = None

    def __init__(self, *args):
        threading.Thread.__init__(self, *args)

    @staticmethod
    def get_data_hash(items):

        m = hashlib.md5()
        for item in items:
            item_string = "%s_%s_%s_%s_%s_%s" % (
                item.name,
                item.play_count,
                item.favorite,
                item.resume_time,
                item.recursive_unplayed_items_count,
                item.etag
            )
            item_string = item_string.encode("UTF-8")
            m.update(item_string)

        return m.hexdigest()

    def run(self):

        log.debug("CacheManagerThread : Started")

        home_window = HomeWindow()

        if self.cached_data is None and self.fresh_data is not None:

            loops = 0
            wait_refresh = home_window.getProperty(self.cache_file)
            while wait_refresh and loops < 200 and not xbmc.Monitor().abortRequested():
                log.debug("CacheManagerThread: wait_refresh")
                xbmc.sleep(100)
                loops = loops + 1
                wait_refresh = home_window.getProperty(self.cache_file)

            log.debug("CacheManagerThread : Saving New Data loops({0})", loops)

            with open(self.cache_file, 'wb') as handle:
                cPickle.dump(self.fresh_data, handle, protocol=cPickle.HIGHEST_PROTOCOL)

            home_window.clearProperty(self.cache_file)

        else:

            cached_hash = self.get_data_hash(self.cached_data)
            log.debug("CacheManagerThread : Cache Hash : {0}", cached_hash)

            data_manager = DataManager()
            results = data_manager.GetContent(self.cache_url)
            if results is None:
                results = []

            if isinstance(results, dict) and results.get("Items") is not None:
                results = results.get("Items", [])
            elif isinstance(results, list) and len(results) > 0 and results[0].get("Items") is not None:
                results = results[0].get("Items")

            loaded_items = []
            for item in results:
                item_data = extract_item_info(item, self.gui_options)
                loaded_items.append(item_data)

            loaded_hash = self.get_data_hash(loaded_items)
            log.debug("CacheManagerThread : Loaded Hash : {0}", loaded_hash)

            # if they dont match then save the data and trigger a content reload
            if cached_hash != loaded_hash:
                log.debug("CacheManagerThread : Saving new cache data and reloading container")

                # we need to refresh but will wait until the main function has finished
                loops = 0
                wait_refresh = home_window.getProperty(self.cache_file)
                while wait_refresh and loops < 200 and not xbmc.Monitor().abortRequested():
                    log.debug("CacheManagerThread: wait_refresh")
                    xbmc.sleep(100)
                    loops = loops + 1
                    wait_refresh = home_window.getProperty(self.cache_file)

                with open(self.cache_file, 'wb') as handle:
                    cPickle.dump(loaded_items, handle, protocol=cPickle.HIGHEST_PROTOCOL)

                home_window.clearProperty(self.cache_file)
                log.debug("CacheManagerThread : Sending container refresh ({0})", loops)
                xbmc.executebuiltin("Container.Refresh")

        log.debug("CacheManagerThread : Exited")
