from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import sys

import xbmcgui
import xbmcplugin
import xbmcaddon

from .lazylogger import LazyLogger

log = LazyLogger(__name__)
addon = xbmcaddon.Addon()


class HomeWindow:
    """
        xbmcgui.Window(10000) with add-on id prefixed to keys
    """

    def __init__(self):
        self.id_string = 'plugin.video.jellycon-%s'
        self.window = xbmcgui.Window(10000)

    def get_property(self, key):
        key = self.id_string % key
        value = self.window.getProperty(key)
        return value

    def set_property(self, key, value):
        key = self.id_string % key
        self.window.setProperty(key, value)

    def clear_property(self, key):
        key = self.id_string % key
        self.window.clearProperty(key)


def add_menu_directory_item(label, path, folder=True, art=None, properties=None):
    li = xbmcgui.ListItem(label, path=path, offscreen=True)
    if art is None:
        art = {}
        art["thumb"] = addon.getAddonInfo('icon')
    if properties is not None:
        li.setProperties(properties)
    li.setArt(art)

    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=folder)
