from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
from .loghandler import LazyLogger
from kodi_six.utils import py2_encode

log = LazyLogger(__name__)
addon = xbmcaddon.Addon()


def string_load(string_id):
    try:
        return py2_encode(addon.getLocalizedString(string_id))
    except Exception as e:
        log.error('Failed String Load: {0} ({1})', string_id, e)
        return str(string_id)
