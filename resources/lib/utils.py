# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
import xbmc
import xbmcvfs
from kodi_six.utils import py2_encode, py2_decode

import binascii
import string
import random
import json
import base64
import time
import math
from datetime import datetime
import calendar
import re
from uuid import uuid4
from six import ensure_text, ensure_binary
from six.moves.urllib.parse import urlencode

from .loghandler import LazyLogger
from .kodi_utils import HomeWindow

# hack to get datetime strptime loaded
throwaway = time.strptime('20110101', '%Y%m%d')

log = LazyLogger(__name__)


def get_jellyfin_url(base_url, params):
    params["format"] = "json"
    url_params = urlencode(params)
    # Filthy hack until I get around to reworking the network flow
    # It relies on {thing} strings in downloadutils.py
    url_params = url_params.replace('%7B', '{').replace('%7D', '}')
    return base_url + "?" + url_params


def get_checksum(item):
    userdata = item['UserData']
    checksum = "%s_%s_%s_%s_%s_%s_%s" % (
        item['Etag'],
        userdata['Played'],
        userdata['IsFavorite'],
        userdata.get('Likes', "-"),
        userdata['PlaybackPositionTicks'],
        userdata.get('UnplayedItemCount', "-"),
        userdata.get("PlayedPercentage", "-")
    )

    return checksum


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def single_urlencode(text):
    # urlencode needs a utf- string
    text = urlencode({'blahblahblah': text.encode('utf-8')})
    text = text[13:]
    return text.decode('utf-8')  # return the result again as unicode


def send_event_notification(method, data=None, hexlify=False):
    '''
    Send events through Kodi's notification system
    '''
    data = data or {}

    if hexlify:
        # Used exclusively for the upnext plugin
        data = ensure_text(binascii.hexlify(ensure_binary(json.dumps(data))))
    sender = 'plugin.video.jellycon'
    data = '"[%s]"' % json.dumps(data).replace('"', '\\"')

    xbmc.executebuiltin('NotifyAll(%s, %s, %s)' % (sender, method, data))


def datetime_from_string(time_string):

    if time_string[-1:] == "Z":
        time_string = re.sub("[0-9]{1}Z", " UTC", time_string)
    elif time_string[-6:] == "+00:00":
        time_string = re.sub("[0-9]{1}\+00:00", " UTC", time_string)
    log.debug("New Time String : {0}".format(time_string))

    start_time = time.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")
    dt = datetime(*(start_time[0:6]))
    timestamp = calendar.timegm(dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    local_dt.replace(microsecond=dt.microsecond)
    return local_dt


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def translate(string_id):
    try:
        addon = xbmcaddon.Addon()
        return py2_encode(addon.getLocalizedString(string_id))
    except Exception as e:
        log.error('Failed String Load: {0} ({1})', string_id, e)
        return str(string_id)


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

def get_version():
    addon = xbmcaddon.Addon()
    version = addon.getAddonInfo("version")
    return version
