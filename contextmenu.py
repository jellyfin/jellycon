# -*- coding: utf-8 -*-

#################################################################################################

import logging
import os
import sys

import xbmc
import xbmcaddon

from resources.lib.functions import show_menu
from resources.lib.simple_logging import SimpleLogging

log = SimpleLogging('contextmenu')

item_id = sys.listitem.getProperty("id")
log.debug("Context Menu Item ID: {0}", item_id)

params = {}
params["item_id"] = item_id
show_menu(params)
