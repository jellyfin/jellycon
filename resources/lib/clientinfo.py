# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

from uuid import uuid4
from kodi_six.utils import py2_decode
import xbmcaddon
import xbmc
import xbmcvfs

from .kodi_utils import HomeWindow
from .loghandler import LazyLogger

log = LazyLogger(__name__)


class ClientInformation:

    @staticmethod
    def get_device_id():

        window = HomeWindow()
        client_id = window.get_property("client_id")

        if client_id:
            return client_id

        jellyfin_guid_path = py2_decode(xbmc.translatePath("special://temp/jellycon_guid"))
        log.debug("jellyfin_guid_path: {0}".format(jellyfin_guid_path))
        guid = xbmcvfs.File(jellyfin_guid_path)
        client_id = guid.read()
        guid.close()

        if not client_id:
            # Needs to be captilized for backwards compat
            client_id = uuid4().hex.upper()
            log.debug("Generating a new guid: {0}".format(client_id))
            guid = xbmcvfs.File(jellyfin_guid_path, 'w')
            guid.write(client_id)
            guid.close()
            log.debug("jellyfin_client_id (NEW): {0}".format(client_id))
        else:
            log.debug("jellyfin_client_id: {0}".format(client_id))

        window.set_property("client_id", client_id)
        return client_id

    @staticmethod
    def get_version():
        addon = xbmcaddon.Addon()
        version = addon.getAddonInfo("version")
        return version

    @staticmethod
    def get_client():
        return 'Kodi JellyCon'
