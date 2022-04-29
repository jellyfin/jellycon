# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
import xbmc
import xbmcvfs
from kodi_six.utils import py2_encode, py2_decode
import sys

import binascii
import string
import random
import json
import time
import math
import os
import hashlib
from datetime import datetime
from dateutil import tz
import time
import re
from uuid import uuid4
from six import ensure_text, ensure_binary, text_type
from six.moves.urllib.parse import urlencode

from .lazylogger import LazyLogger
from .kodi_utils import HomeWindow

# hack to get datetime strptime loaded
throwaway = time.strptime('20110101', '%Y%m%d')

log = LazyLogger(__name__)


def kodi_version():
    # Kodistubs returns empty string, causing Python 3 tests to choke on int()
    # TODO: Make Kodistubs version configurable for testing purposes
    if sys.version_info.major == 2:
        default_versionstring = "18"
    else:
        default_versionstring = "19.1 (19.1.0) Git:20210509-85e05228b4"

    version_string = xbmc.getInfoLabel('System.BuildVersion') or default_versionstring
    return int(version_string.split(' ', 1)[0].split('.', 1)[0])


def get_jellyfin_url(path, params):
    params["format"] = "json"
    url_params = urlencode(params)
    return '{}?{}'.format(path, url_params)


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

    try:
        dt = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")
    except TypeError:
        # https://bugs.python.org/issue27400
        dt = datetime(*(time.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f %Z")[0:6]))

    # Convert server dates from UTC to local time
    utc = tz.tzutc()
    local = tz.tzlocal()

    utc_dt = dt.replace(tzinfo=utc)
    local_dt = utc_dt.astimezone(local)

    return local_dt


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

    jellyfin_guid_path = py2_decode(translate_path("special://temp/jellycon_guid"))
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
    addon_data = translate_path(xbmcaddon.Addon().getAddonInfo('profile'))

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
    addon_data = translate_path(xbmcaddon.Addon().getAddonInfo('profile'))

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


def get_art_url(data, art_type, parent=False, index=0, server=None):

    item_id = data["Id"]
    item_type = data["Type"]

    if item_type in ["Episode", "Season"]:
        if art_type != "Primary" or parent is True:
            item_id = data["SeriesId"]

    image_tag = ""

    # for episodes always use the parent BG
    if item_type == "Episode" and art_type == "Backdrop":
        item_id = data.get("ParentBackdropItemId")
        bg_item_tags = data.get("ParentBackdropImageTags", [])
        if bg_item_tags:
            image_tag = bg_item_tags[0]
    elif art_type == "Backdrop" and parent is True:
        item_id = data.get("ParentBackdropItemId")
        bg_item_tags = data.get("ParentBackdropImageTags", [])
        if bg_item_tags:
            image_tag = bg_item_tags[0]
    elif art_type == "Backdrop":
        bg_tags = data.get("BackdropImageTags", [])
        if bg_tags:
            image_tag = bg_tags[index]
    elif parent is False:
        image_tags = data.get("ImageTags", [])
        if image_tags:
            image_tag_type = image_tags.get(art_type)
            if image_tag_type:
                image_tag = image_tag_type
    elif parent is True:
        if (item_type == "Episode" or item_type == "Season") and art_type == 'Primary':
            tag_name = 'SeriesPrimaryImageTag'
            id_name = 'SeriesId'
        else:
            tag_name = 'Parent%sImageTag' % art_type
            id_name = 'Parent%sItemId' % art_type
        parent_image_id = data.get(id_name)
        parent_image_tag = data.get(tag_name)
        if parent_image_id is not None and parent_image_tag is not None:
            item_id = parent_image_id
            image_tag = parent_image_tag

    # ParentTag not passed for Banner and Art
    if not image_tag and not ((art_type == 'Banner' or art_type == 'Art') and parent is True):
        return ""

    artwork = "{}/Items/{}/Images/{}/{}?Format=original&Tag={}".format(
        server, item_id, art_type, index, image_tag)
    return artwork


def image_url(item_id, art_type, index, width, height, image_tag, server):

    # test imageTag e3ab56fe27d389446754d0fb04910a34
    artwork = "{}/Items/{}/Images/{}/{}?Format=original&Tag={}".format(server, item_id, art_type, index, image_tag)
    if int(width) > 0:
        artwork += '&MaxWidth={}'.format(width)
    if int(height) > 0:
        artwork += '&MaxHeight={}'.format(height)

    return artwork


def get_default_filters():

    addon_settings = xbmcaddon.Addon()
    include_media = addon_settings.getSetting("include_media") == "true"
    include_people = addon_settings.getSetting("include_people") == "true"
    include_overview = addon_settings.getSetting("include_overview") == "true"

    filer_list = [
        "DateCreated",
        "EpisodeCount",
        "SeasonCount",
        "Path",
        "Genres",
        "Studios",
        "Etag",
        "Taglines",
        "SortName",
        "RecursiveItemCount",
        "ChildCount",
        "ProductionLocations",
        "CriticRating",
        "OfficialRating",
        "CommunityRating",
        "PremiereDate",
        "ProductionYear",
        "AirTime",
        "Status",
        "Tags"
    ]

    if include_media:
        filer_list.append("MediaStreams")

    if include_people:
        filer_list.append("People")

    if include_overview:
        filer_list.append("Overview")

    return ','.join(filer_list)


def translate_path(path):
    '''
    Use new library location for translate path starting in Kodi 19
    '''
    version = kodi_version()

    if version > 18:
        return xbmcvfs.translatePath(path)
    else:
        return xbmc.translatePath(path)
