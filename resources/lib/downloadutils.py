# Gnu General Public License - see LICENSE.TXT
from __future__ import division, absolute_import, print_function, unicode_literals

import xbmcgui
import xbmcaddon

import requests
import json
from six.moves.urllib.parse import urlparse
from base64 import b64encode
from collections import defaultdict
from traceback import format_exc
from kodi_six.utils import py2_decode

from .kodi_utils import HomeWindow
from .loghandler import LazyLogger
from .tracking import timer
from .utils import get_device_id, get_version, translate_string, load_user_details, save_user_details

log = LazyLogger(__name__)


def get_details_string():

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

    return ",".join(filer_list)


class DownloadUtils:
    use_https = False
    verify_cert = False

    def __init__(self, *args):
        settings = xbmcaddon.Addon()

        self.use_https = False
        if settings.getSetting('protocol') == "1":
            self.use_https = True
        log.debug("use_https: {0}".format(self.use_https))

        self.verify_cert = settings.getSetting('verify_cert') == 'true'
        log.debug("verify_cert: {0}".format(self.verify_cert))

    def post_capabilities(self):

        url = "{server}/Sessions/Capabilities/Full?format=json"
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

        self.download_url(url, post_body=data, method="POST")
        log.debug("Posted Capabilities: {0}".format(data))

    def get_item_playback_info(self, item_id, force_transcode):

        addon_settings = xbmcaddon.Addon()

        filtered_codecs = []
        if addon_settings.getSetting("force_transcode_h265") == "true":
            filtered_codecs.append("hevc")
            filtered_codecs.append("h265")
        if addon_settings.getSetting("force_transcode_mpeg2") == "true":
            filtered_codecs.append("mpeg2video")
        if addon_settings.getSetting("force_transcode_msmpeg4v3") == "true":
            filtered_codecs.append("msmpeg4v3")
        if addon_settings.getSetting("force_transcode_mpeg4") == "true":
            filtered_codecs.append("mpeg4")

        playback_bitrate = addon_settings.getSetting("max_stream_bitrate")
        force_playback_bitrate = addon_settings.getSetting("force_max_stream_bitrate")
        if force_transcode:
            playback_bitrate = force_playback_bitrate

        audio_codec = addon_settings.getSetting("audio_codec")
        audio_playback_bitrate = addon_settings.getSetting("audio_playback_bitrate")
        audio_max_channels = addon_settings.getSetting("audio_max_channels")

        audio_bitrate = int(audio_playback_bitrate) * 1000
        bitrate = int(playback_bitrate) * 1000

        profile = {
            "Name": "Kodi",
            "MaxStaticBitrate": bitrate,
            "MaxStreamingBitrate": bitrate,
            "MusicStreamingTranscodingBitrate": audio_bitrate,
            "TimelineOffsetSeconds": 5,
            "TranscodingProfiles": [
                {
                    "Type": "Audio"
                },
                {
                    "Container": "ts",
                    "Protocol": "hls",
                    "Type": "Video",
                    "AudioCodec": audio_codec,
                    "VideoCodec": "h264",
                    "MaxAudioChannels": audio_max_channels
                },
                {
                    "Container": "jpeg",
                    "Type": "Photo"
                }
            ],
            "DirectPlayProfiles": [
                {
                    "Type": "Video"
                },
                {
                    "Type": "Audio"
                },
                {
                    "Type": "Photo"
                }
            ],
            "ResponseProfiles": [],
            "ContainerProfiles": [],
            "CodecProfiles": [],
            "SubtitleProfiles": [
                {
                    "Format": "srt",
                    "Method": "External"
                },
                {
                    "Format": "srt",
                    "Method": "Embed"
                },
                {
                    "Format": "ass",
                    "Method": "External"
                },
                {
                    "Format": "ass",
                    "Method": "Embed"
                },
                {
                    "Format": "sub",
                    "Method": "Embed"
                },
                {
                    "Format": "sub",
                    "Method": "External"
                },
                {
                    "Format": "ssa",
                    "Method": "Embed"
                },
                {
                    "Format": "ssa",
                    "Method": "External"
                },
                {
                    "Format": "smi",
                    "Method": "Embed"
                },
                {
                    "Format": "smi",
                    "Method": "External"
                },
                {
                    "Format": "pgssub",
                    "Method": "Embed"
                },
                {
                    "Format": "pgssub",
                    "Method": "External"
                },
                {
                    "Format": "dvdsub",
                    "Method": "Embed"
                },
                {
                    "Format": "dvdsub",
                    "Method": "External"
                },
                {
                    "Format": "pgs",
                    "Method": "Embed"
                },
                {
                    "Format": "pgs",
                    "Method": "External"
                }
            ]
        }

        if len(filtered_codecs) > 0:
            profile['DirectPlayProfiles'][0]['VideoCodec'] = "-%s" % ",".join(filtered_codecs)

        if force_transcode:
            profile['DirectPlayProfiles'] = []

        if addon_settings.getSetting("playback_video_force_8") == "true":
            profile['CodecProfiles'].append(
                {
                    "Type": "Video",
                    "Codec": "h264",
                    "Conditions": [
                        {
                            "Condition": "LessThanEqual",
                            "Property": "VideoBitDepth",
                            "Value": "8",
                            "IsRequired": False
                        }
                    ]
                }
            )
            profile['CodecProfiles'].append(
                {
                    "Type": "Video",
                    "Codec": "h265,hevc",
                    "Conditions": [
                        {
                            "Condition": "EqualsAny",
                            "Property": "VideoProfile",
                            "Value": "main"
                        }
                    ]
                }
            )

        playback_info = {
            'UserId': self.get_user_id(),
            'DeviceProfile': profile,
            'AutoOpenLiveStream': True
        }

        if force_transcode:
            url = "{server}/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s&EnableDirectPlay=false&EnableDirectStream=false" % (item_id, bitrate)
        else:
            url = "{server}/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s" % (item_id, bitrate)

        log.debug("PlaybackInfo : {0}".format(url))
        log.debug("PlaybackInfo : {0}".format(profile))
        play_info_result = self.download_url(url, post_body=playback_info, method="POST")
        log.debug("PlaybackInfo : {0}".format(play_info_result))

        return play_info_result

    def get_server(self):
        settings = xbmcaddon.Addon()

        # For migration from storing URL parts to just one URL
        if settings.getSetting('ipaddress') != "" and settings.getSetting('ipaddress') != "&lt;none&gt;":
            log.info("Migrating to new server url storage")
            url = ("http://" if settings.getSetting('protocol') == "0" else "https://") + settings.getSetting('ipaddress') + ":" + settings.getSetting('port')
            settings.setSetting('server_address', url)
            settings.setSetting('ipaddress', "")

        return settings.getSetting('server_address')

    @staticmethod
    def get_all_artwork(item, server):
        all_art = defaultdict(lambda: "")

        item_id = item["Id"]
        item_type = item["Type"]
        image_tags = item["ImageTags"]

        # All the image tags
        for tag_name in image_tags:
            tag = image_tags[tag_name]
            art_url = "%s/Items/%s/Images/%s/0?Format=original&Tag=%s" % (server, item_id, tag_name, tag)
            all_art[tag_name] = art_url

        # Series images
        if item_type in ["Episode", "Season"]:
            image_tag = item["SeriesPrimaryImageTag"]
            series_id = item["SeriesId"]
            if image_tag and series_id:
                art_url = "%s/Items/%s/Images/Primary/0?Format=original&Tag=%s" % (server, series_id, image_tag)
                all_art["Primary.Series"] = art_url

        return all_art

    def get_artwork(self, data, art_type, parent=False, index=0, server=None):

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

        artwork = "%s/Items/%s/Images/%s/%s?Format=original&Tag=%s" % (server, item_id, art_type, index, image_tag)

        if self.use_https and not self.verify_cert:
            artwork += "|verifypeer=false"

        return artwork

    def image_url(self, item_id, art_type, index, width, height, image_tag, server):

        # test imageTag e3ab56fe27d389446754d0fb04910a34
        artwork = "%s/Items/%s/Images/%s/%s?Format=original&Tag=%s" % (server, item_id, art_type, index, image_tag)
        if int(width) > 0:
            artwork += '&MaxWidth=%s' % width
        if int(height) > 0:
            artwork += '&MaxHeight=%s' % height

        if self.use_https and not self.verify_cert:
            artwork += "|verifypeer=false"

        return artwork

    def get_user_artwork(self, user, item_type):

        if "PrimaryImageTag" not in user:
            return ""
        user_id = user.get("Id")
        tag = user.get("PrimaryImageTag")
        server = self.get_server()

        artwork = "%s/Users/%s/Images/%s?Format=original&tag=%s" % (server, user_id, item_type, tag)

        if self.use_https and not self.verify_cert:
            artwork += "|verifypeer=false"

        return artwork


    def get_user_id(self):
        user_details = load_user_details()
        user_id = user_details.get('user_id', '')
        return user_id


    def authenticate(self):
        window = HomeWindow()
        user_name = window.get_property('user_name')
        user_details = load_user_details()

        if user_details.get('token', ''):
            log.debug("JellyCon DownloadUtils -> Returning saved AccessToken")
            # Resave credentials to update settings file
            save_user_details(user_details.get('user_name'),
                              user_details.get('user_id'),
                              user_details.get('token'))
            return user_details.get('token')

        settings = xbmcaddon.Addon()

        url = "{server}/Users/AuthenticateByName"

        '''
        TODO: Make the authenticate function operate with arguments during
        network rework.  Password could be leaked like this, but it's better
        than it was previously
        '''
        password = window.get_property('password')
        window.clear_property('password')
        message_data = {'username': user_name, 'pw': password}

        result = self.download_url(url, post_body=message_data, method="POST", suppress=True, authenticate=False)

        access_token = result.get("AccessToken")
        userid = result["User"].get("Id")

        if access_token is not None:
            log.debug('User authenticated successfully')
            save_user_details(user_name, userid, access_token)
            self.post_capabilities()
        else:
            log.debug("User NOT Authenticated")

    def get_auth_header(self, authenticate=True):
        device_id = get_device_id()
        version = get_version()
        client = 'Kodi JellyCon'

        settings = xbmcaddon.Addon()
        device_name = settings.getSetting('deviceName')
        # remove none ascii chars
        device_name = py2_decode(device_name)
        # remove some chars not valid for names
        device_name = device_name.replace("\"", "_")
        if len(device_name) == 0:
            device_name = "JellyCon"

        headers = {}
        headers["Accept-encoding"] = "gzip"
        headers["Accept-Charset"] = "UTF-8,*"

        if authenticate is False:
            auth_string = 'MediaBrowser Client="{}",Device="{}",DeviceId="{}",Version="{}'.format(client, device_name, device_id, version)
            headers['X-Emby-Authorization'] = auth_string
            return headers
        else:
            userid = self.get_user_id()
            auth_string = 'MediaBrowser UserId="{}",Client="{}",Device="{}",DeviceId="{}",Version="{}"'.format(userid, client, device_name, device_id, version)
            headers['X-Emby-Authorization'] = auth_string

            auth_token = self.authenticate()
            if auth_token != "":
                headers["X-MediaBrowser-Token"] = auth_token

            log.debug("JellyCon Authentication Header: {0}".format(headers))
            return headers

    @timer
    def download_url(self, url, suppress=False, post_body=None, method="GET", authenticate=True, headers=None):
        log.debug("downloadUrl")

        home_window = HomeWindow()
        settings = xbmcaddon.Addon()
        user_details = load_user_details()
        username = user_details.get('user_name')
        user_id = user_details.get('user_id', '')
        server = None

        http_timeout = int(settings.getSetting("http_timeout"))

        if authenticate and username == "":
            return {}

        if settings.getSetting("suppressErrors") == "true":
            suppress = True

        log.debug("Before: {0}".format(url))

        if url.find("{server}") != -1:
            server = self.get_server()
            if server is None:
                return {}
            url = url.replace("{server}", server)

        if url.find("{userid}") != -1:
            url = url.replace("{userid}", user_id)

        if url.find("{ItemLimit}") != -1:
            show_x_filtered_items = settings.getSetting("show_x_filtered_items")
            url = url.replace("{ItemLimit}", show_x_filtered_items)

        if url.find("{field_filters}") != -1:
            filter_string = get_details_string()
            url = url.replace("{field_filters}", filter_string)

        if url.find("{random_movies}") != -1:
            random_movies = home_window.get_property("random-movies")
            if not random_movies:
                return {}
            url = url.replace("{random_movies}", random_movies)

        log.debug("After: {0}".format(url))

        try:
            url_bits = urlparse(url.strip())
            user_name = url_bits.username
            user_password = url_bits.password

            head = self.get_auth_header(authenticate)

            if user_name and user_password:
                log.info("Replacing username & Password info")
                # add basic auth headers
                user_and_pass = b64encode(b"%s:%s" % (user_name, user_password)).decode("ascii")
                head["Authorization"] = 'Basic %s' % user_and_pass

            head["User-Agent"] = "JellyCon-" + get_version()

            http_request = getattr(requests, method.lower())

            if post_body:

                if isinstance(post_body, dict):
                    head["Content-Type"] = "application/json"
                    post_body = json.dumps(post_body)
                else:
                    head["Content-Type"] = "application/x-www-form-urlencoded"

                log.debug("Content-Type: {0}".format(head["Content-Type"]))
                log.debug("POST DATA: {0}".format(post_body))

                data = http_request(url, data=post_body, headers=head)
            else:
                data = http_request(url, headers=head)

            if data.status_code == 200:

                if headers is not None and isinstance(headers, dict):
                    headers.update(data.headers)
                log.debug("{0}".format(data.json()))

            elif data.status_code >= 400:

                if data.status_code == 401:
                    # remove any saved password
                    log.error("HTTP response error 401 auth error, removing any saved passwords for user: {0}".format(username))
                    save_user_details(username, user_id, '')

                log.error("HTTP response error for {0}: {1} {2}".format(url, data.status_code, data.content))
                if suppress is False:
                    xbmcgui.Dialog().notification(translate_string(30316),
                                                  '{}: {}'.format(translate_string(30200), data.content),
                                                  icon="special://home/addons/plugin.video.jellycon/icon.png")
            try:
                result = data.json()
            except:
                result = {}
            return result
        except Exception as msg:
            log.error("{0}".format(format_exc()))
            log.error("Unable to connect to {0} : {1}".format(server, msg))
            if not suppress:
                xbmcgui.Dialog().notification(translate_string(30316),
                                              str(msg),
                                              icon="special://home/addons/plugin.video.jellycon/icon.png")
