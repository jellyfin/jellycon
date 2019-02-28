# Gnu General Public License - see LICENSE.TXT

import json
from collections import defaultdict
import threading
import hashlib
import os
import cPickle
import time
#import copy
#import urllib

from .downloadutils import DownloadUtils
from .simple_logging import SimpleLogging
from .item_functions import extract_item_info
from .kodi_utils import HomeWindow

import xbmc
import xbmcaddon

log = SimpleLogging(__name__)


class CacheItem():
    item_list = None
    item_list_hash = None
    date_saved = None
    last_action = None
    items_url = None
    file_path = None

    def __init__(self, *args):
        pass


class DataManager():

    addon_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    def __init__(self, *args):
        # log.debug("DataManager __init__")
        pass

    def loadJasonData(self, jsonData):
        return json.loads(jsonData, object_hook=lambda d: defaultdict(lambda: None, d))

    def GetContent(self, url):
        jsonData = DownloadUtils().downloadUrl(url)
        result = self.loadJasonData(jsonData)
        return result

    def get_items(self, url, gui_options, use_cache=False):

        home_window = HomeWindow()
        log.debug("last_content_url : use_cache={0} url={1}", use_cache, url)
        home_window.setProperty("last_content_url", url)

        download_utils = DownloadUtils()
        user_id = download_utils.getUserId()
        server = download_utils.getServer()

        m = hashlib.md5()
        m.update(user_id + "|" + server + "|" + url)
        url_hash = m.hexdigest()
        cache_file = os.path.join(self.addon_dir, "cache_" + url_hash + ".pickle")

        #changed_url = url + "&MinDateLastSavedForUser=" + urllib.unquote("2019-09-16T13:45:30")
        #results = self.GetContent(changed_url)
        #log.debug("DataManager Changes Since Date : {0}", results)

        item_list = None
        total_records = 0
        baseline_name = None
        cache_thread = CacheManagerThread()
        cache_thread.gui_options = gui_options

        home_window.setProperty(cache_file, "true")

        clear_cache = home_window.getProperty("skip_cache_for_" + url)
        if clear_cache and os.path.isfile(cache_file):
            log.debug("Clearing cache data and loading new data")
            home_window.clearProperty("skip_cache_for_" + url)
            os.remove(cache_file)

        # try to load the list item data from the cache
        if os.path.isfile(cache_file) and use_cache:
            log.debug("Loading url data from cached pickle data")

            with open(cache_file, 'rb') as handle:
                try:
                    cache_item = cPickle.load(handle)
                    cache_thread.cached_item = cache_item
                    item_list = cache_item.item_list
                    total_records = cache_item.total_records
                except Exception as err:
                    log.debug("Pickle Data Load Failed : {0}", err)
                    item_list = None

        # we need to load the list item data form the server
        if item_list is None:
            log.debug("Loading url data from server")

            results = self.GetContent(url)

            if results is None:
                results = []

            if isinstance(results, dict):
                total_records = results.get("TotalRecordCount", 0)

            if isinstance(results, dict) and results.get("Items") is not None:
                baseline_name = results.get("BaselineItemName")
                results = results.get("Items", [])
            elif isinstance(results, list) and len(results) > 0 and results[0].get("Items") is not None:
                baseline_name = results[0].get("BaselineItemName")
                results = results[0].get("Items")

            item_list = []
            for item in results:
                item_data = extract_item_info(item, gui_options)
                item_data.baseline_itemname = baseline_name
                item_list.append(item_data)

            cache_item = CacheItem()
            cache_item.item_list = item_list
            cache_item.file_path = cache_file
            cache_item.items_url = url
            cache_item.last_action = "fresh_data"
            cache_item.date_saved = time.time()
            cache_item.total_records = total_records

            cache_thread.cached_item = cache_item
            # copy.deepcopy(item_list)

        if use_cache:
            cache_thread.start()

        return cache_file, item_list, total_records


class CacheManagerThread(threading.Thread):
    cached_item = None
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

    def wait_for_save(self, home_window, file_name):
        loops = 0
        wait_refresh = home_window.getProperty(file_name)
        while wait_refresh and loops < 200 and not xbmc.Monitor().abortRequested():
            xbmc.sleep(100)
            loops = loops + 1
            wait_refresh = home_window.getProperty(file_name)
        return loops

    def run(self):

        log.debug("CacheManagerThread : Started")

        home_window = HomeWindow()
        is_fresh = False

        # if the data is fresh then just save it
        # if the data is to old do a reload
        if (self.cached_item.date_saved is not None
                and (time.time() - self.cached_item.date_saved) < 20
                and self.cached_item.last_action == "fresh_data"):
            is_fresh = True

        if is_fresh:
            log.debug("CacheManagerThread : Saving fresh data")
            cached_hash = self.get_data_hash(self.cached_item.item_list)
            self.cached_item.item_list_hash = cached_hash
            self.cached_item.last_action = "cached_data"
            self.cached_item.date_saved = time.time()

            loops = self.wait_for_save(home_window, self.cached_item.file_path)

            log.debug("CacheManagerThread : Saving New Data loops({0})", loops)

            with open(self.cached_item.file_path, 'wb') as handle:
                cPickle.dump(self.cached_item, handle, protocol=cPickle.HIGHEST_PROTOCOL)

            home_window.clearProperty(self.cached_item.file_path)

        else:
            log.debug("CacheManagerThread : Reloading to recheck data hashes")
            cached_hash = self.cached_item.item_list_hash
            log.debug("CacheManagerThread : Cache Hash : {0}", cached_hash)

            data_manager = DataManager()
            results = data_manager.GetContent(self.cached_item.items_url)
            if results is None:
                results = []

            if isinstance(results, dict) and results.get("Items") is not None:
                results = results.get("Items", [])
            elif isinstance(results, list) and len(results) > 0 and results[0].get("Items") is not None:
                results = results[0].get("Items")

            total_records = 0
            if isinstance(results, dict):
                total_records = results.get("TotalRecordCount", 0)

            loaded_items = []
            for item in results:
                item_data = extract_item_info(item, self.gui_options)
                loaded_items.append(item_data)

            loaded_hash = self.get_data_hash(loaded_items)
            log.debug("CacheManagerThread : Loaded Hash : {0}", loaded_hash)

            # if they dont match then save the data and trigger a content reload
            if cached_hash != loaded_hash:
                log.debug("CacheManagerThread : Hashes different, saving new data and reloading container")

                self.cached_item.item_list = loaded_items
                self.cached_item.item_list_hash = loaded_hash
                self.cached_item.last_action = "fresh_data"
                self.cached_item.date_saved = time.time()
                self.cached_item.total_records = total_records

                # we need to refresh but will wait until the main function has finished
                loops = self.wait_for_save(home_window, self.cached_item.file_path)

                with open(self.cached_item.file_path, 'wb') as handle:
                    cPickle.dump(self.cached_item, handle, protocol=cPickle.HIGHEST_PROTOCOL)

                home_window.clearProperty(self.cached_item.file_path)
                log.debug("CacheManagerThread : Sending container refresh ({0})", loops)
                xbmc.executebuiltin("Container.Refresh")

        log.debug("CacheManagerThread : Exited")
