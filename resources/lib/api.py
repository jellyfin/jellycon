from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcaddon
from kodi_six.utils import py2_decode

import requests

from .utils import get_device_id, get_version
from .loghandler import LazyLogger

log = LazyLogger(__name__)


class API:
    def __init__(self, server=None, user_id=None, token=None):
        self.server = server
        self.user_id = user_id
        self.token = token

        self.settings = xbmcaddon.Addon()

        self.headers = {}
        self.create_headers()

    def get(self, path):
        if not self.headers:
            self.create_headers()

        url = '{}{}'.format(self.server, path)

        r = requests.get(url, headers=self.headers)
        return r.json()

    def post(self, url, payload):
        if not self.headers:
            self.create_headers()

        url = '{}{}'.format(self.server, url)

        r = requests.post(url, json=payload, headers=self.headers)
        try:
            response_data = r.json()
        except:
            response_data = {}
        return response_data

    def delete(self, url):
        url = '{}{}'.format(self.server, url)

        requests.delete(url, headers=self.headers)

    def authenticate(self, auth_data):
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

    def create_headers(self):

        # If the headers already exist with an auth token, return
        if self.headers and 'x-mediabrowser-token' in self.headers:
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

        # If we have a valid token, ensure it's included in the headers
        if self.token:
            headers['x-mediabrowser-token'] = self.token

        # Make headers available to api calls
        self.headers = headers

    def post_capabilities(self):
        url = '{}/Sessions/Capabilities/Full'.format(self.server)

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
        response = requests.get(url, stream=True, headers=self.headers)

        return response
