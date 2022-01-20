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
import time
import math
import os
import hashlib
from datetime import datetime
import re
from uuid import uuid4
from six import ensure_text, ensure_binary, text_type
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

    # Builtin python library can't handle ISO-8601 well. Make it compatible
    if time_string[-1:] == "Z":
        time_string = re.sub("[0-9]{1}Z", " UTC", time_string)
    elif time_string[-6:] == "+00:00":
        time_string = re.sub("[0-9]{1}\+00:00", " UTC", time_string)

    dt = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")

    return dt


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def translate_string(string_id):
    try:
        addon = xbmcaddon.Addon()
        return py2_encode(addon.getLocalizedString(string_id))
    except Exception as e:
        log.error('Failed String Load: {0} ({1})', string_id, e)
        return str(string_id)


def get_device_id():

    window = HomeWindow()
    username = window.get_property('username')
    client_id = window.get_property("client_id")
    hashed_name = hashlib.md5(username.encode()).hexdigest()

    if client_id:
        return '{}-{}'.format(client_id, hashed_name)

    jellyfin_guid_path = py2_decode(xbmc.translatePath("special://temp/jellycon_guid"))
    log.debug("jellyfin_guid_path: {0}".format(jellyfin_guid_path))
    guid = xbmcvfs.File(jellyfin_guid_path)
    client_id = guid.read()
    guid.close()

    if not client_id:
        client_id = uuid4().hex
        log.debug("Generating a new guid: {0}".format(client_id))
        guid = xbmcvfs.File(jellyfin_guid_path, 'w')
        guid.write(client_id)
        guid.close()
        log.debug("jellyfin_client_id (NEW): {0}".format(client_id))
    else:
        log.debug("jellyfin_client_id: {0}".format(client_id))

    window.set_property("client_id", client_id)
    return '{}-{}'.format(client_id, hashed_name)


def get_version():
    addon = xbmcaddon.Addon()
    version = addon.getAddonInfo("version")
    return version


def save_user_details(user_name, user_id, token):
    settings = xbmcaddon.Addon()
    save_user_to_settings = settings.getSetting('save_user_to_settings') == 'true'
    addon_data = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    # Save to a config file for reference later if desired
    if save_user_to_settings:
        try:
            with open(os.path.join(addon_data, 'auth.json'), 'rb') as infile:
                auth_data = json.load(infile)
        except:
            # File doesn't exist or is empty
            auth_data = {}

        auth_data[user_name] = {
            'user_id': user_id,
            'token': token
        }

        with open(os.path.join(addon_data, 'auth.json'), 'wb') as outfile:
            data = json.dumps(auth_data, sort_keys=True, indent=4, ensure_ascii=False)
            if isinstance(data, text_type):
                data = data.encode('utf-8')
            outfile.write(data)

    # Make the username available for easy lookup
    window = HomeWindow()
    settings.setSetting('username', user_name)
    window.set_property('user_name', user_name)


def load_user_details():
    settings = xbmcaddon.Addon()
    window = HomeWindow()
    # Check current variables first, then check settings
    user_name = window.get_property('user_name')
    if not user_name:
        user_name = settings.getSetting('username')
        #settings_user_name = settings.getSetting('username')
    save_user_to_settings = settings.getSetting('save_user_to_settings') == 'true'
    addon_data = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    if save_user_to_settings:
        try:
            with open(os.path.join(addon_data, 'auth.json'), 'rb') as infile:
                auth_data = json.load(infile)
        except:
            # File doesn't exist yet
            return {}

        user_data = auth_data.get(user_name, {})
        user_id = user_data.get('user_id')
        auth_token = user_data.get('token')

        # Payload to return to calling function
        user_details = {}
        user_details['user_name'] = user_name
        user_details['user_id'] = user_id
        user_details['token'] = auth_token
        return user_details

    else:
        return {}
