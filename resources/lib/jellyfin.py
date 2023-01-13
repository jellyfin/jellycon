from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import json

import requests
import xbmcaddon
from kodi_six.utils import py2_decode

from .utils import get_device_id, get_version, load_user_details
from .lazylogger import LazyLogger

log = LazyLogger(__name__)


class API:
    def __init__(self, server=None, user_id=None, token=None):
        self.server = server
        self.user_id = user_id
        self.token = token

        self.settings = xbmcaddon.Addon()

        self.headers = {}
        self.create_headers()
        self.verify_cert = settings.getSetting('verify_cert') == 'true'

    def get(self, path):
        if 'x-mediabrowser-token' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        # Fixes initial login where class is initialized before wizard completes
        if not self.server:
            self.settings = xbmcaddon.Addon()
            self.server = self.settings.getSetting('server_address')

        url = '{}{}'.format(self.server, path)

        r = requests.get(url, headers=self.headers, verify=self.verify_cert)
        try:
            try:
                '''
                The requests library defaults to using simplejson to handle
                json decoding.  On low power devices and using Py3, this is
                significantly slower than the builtin json library.  Skip that
                and just parse the json ourselves.  Fall back to using
                requests/simplejson if there's a parsing error.
                '''
                r.raise_for_status()
                response_data = json.loads(r.text)
            except ValueError:
                response_data = r.json()
        except:  # noqa
            response_data = {}
        return response_data

    def post(self, url, payload={}):
        if 'x-mediabrowser-token' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        url = '{}{}'.format(self.server, url)

        r = requests.post(url, json=payload, headers=self.headers, verify=self.verify_cert)
        try:
            try:
                # Much faster on low power devices, see above comment
                response_data = json.loads(r.text)
            except ValueError:
                response_data = r.json()
        except:  # noqa
            response_data = {}
        return response_data

    def delete(self, url):
        if 'x-mediabrowser-token' not in self.headers or self.token not in self.headers:
            self.create_headers(True)

        url = '{}{}'.format(self.server, url)

        requests.delete(url, headers=self.headers, verify=self.verify_cert)

    def authenticate(self, auth_data):
        # Always force create fresh headers during authentication
        self.create_headers(True)
        response = self.post('/Users/AuthenticateByName', auth_data)
        token = response.get('AccessToken')
        if token:
            self.token = token
            self.user_id = response.get('User').get('Id')
            # Create headers again to include auth token
            self.create_headers()
            return response
        else:
            log.error('Unable to authenticate to Jellyfin server')
            return {}

    def create_headers(self, force=False):

        # If the headers already exist with an auth token, return unless we're regenerating
        if self.headers and 'x-mediabrowser-token' in self.headers and force is False:
            return

        headers = {}
        device_name = self.settings.getSetting('deviceName')
        if len(device_name) == 0:
            device_name = "JellyCon"
        # Ensure ascii and remove invalid characters
        device_name = py2_decode(device_name).replace('"', '_').replace(',', '_')
        device_id = get_device_id()
        version = get_version()

        authorization = (
            'MediaBrowser Client="Kodi JellyCon", Device="{device}", '
            'DeviceId="{device_id}", Version="{version}"'
        ).format(
            device=device_name,
            device_id=device_id,
            version=version
        )

        headers['x-emby-authorization'] = authorization

        # If we have a valid token, ensure it's included in the headers unless we're regenerating
        if self.token and force is False:
            headers['x-mediabrowser-token'] = self.token
        else:
            # Check for updated credentials since initialization
            user_details = load_user_details()
            token = user_details.get('token')
            if token:
                self.token = token
                headers['x-mediabrowser-token'] = self.token

        # Make headers available to api calls
        self.headers = headers

    def post_capabilities(self):
        url = '/Sessions/Capabilities/Full'

        data = {
            'SupportsMediaControl': True,
            'PlayableMediaTypes': ["Video", "Audio"],
            'SupportedCommands': ["MoveUp",
                                  "MoveDown",
                                  "MoveLeft",
                                  "MoveRight",
                                  "Select",
                                  "Back",
                                  "ToggleContextMenu",
                                  "ToggleFullscreen",
                                  "ToggleOsdMenu",
                                  "GoHome",
                                  "PageUp",
                                  "NextLetter",
                                  "GoToSearch",
                                  "GoToSettings",
                                  "PageDown",
                                  "PreviousLetter",
                                  "TakeScreenshot",
                                  "VolumeUp",
                                  "VolumeDown",
                                  "ToggleMute",
                                  "SendString",
                                  "DisplayMessage",
                                  "SetAudioStreamIndex",
                                  "SetSubtitleStreamIndex",
                                  "SetRepeatMode",
                                  "Mute",
                                  "Unmute",
                                  "SetVolume",
                                  "PlayNext",
                                  "Play",
                                  "Playstate",
                                  "PlayMediaSource"]
        }

        self.post(url, data)

    def speedtest(self, test_data_size):
        self.create_headers()

        url = '{}/playback/bitratetest?size={}'.format(self.server, test_data_size)
        # Because this needs the stream argument, this doesn't go through self.get()
        response = requests.get(url, stream=True, headers=self.headers, verify=self.verify_cert)

        return response


settings = xbmcaddon.Addon()
user_details = load_user_details()
api = API(
    settings.getSetting('server_address'),
    user_details.get('user_id'),
    user_details.get('token')
)
