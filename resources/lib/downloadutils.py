# Gnu General Public License - see LICENSE.TXT

import xbmcgui
import xbmcaddon

import httplib
import hashlib
import ssl
import StringIO
import gzip
import json
from urlparse import urlparse
import urllib
from base64 import b64encode
from collections import defaultdict

from .kodi_utils import HomeWindow
from .clientinfo import ClientInformation
from .simple_logging import SimpleLogging
from .translation import string_load
from .tracking import timer

log = SimpleLogging(__name__)


def save_user_details(settings, user_name, user_password):
    save_user_to_settings = settings.getSetting("save_user_to_settings") == "true"
    if save_user_to_settings:
        settings.setSetting("username", user_name)
        settings.setSetting("password", user_password)
    else:
        settings.setSetting("username", "")
        settings.setSetting("password", "")
        home_window = HomeWindow()
        home_window.set_property("username", user_name)
        home_window.set_property("password", user_password)


def load_user_details(settings):
    save_user_to_settings = settings.getSetting("save_user_to_settings") == "true"
    if save_user_to_settings:
        user_name = settings.getSetting("username")
        user_password = settings.getSetting("password")
    else:
        home_window = HomeWindow()
        user_name = home_window.get_property("username")
        user_password = home_window.get_property("password")

    user_details = {}
    user_details["username"] = user_name
    user_details["password"] = user_password
    return user_details


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
        "Status"
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
        log.debug("use_https: {0}", self.use_https)

        self.verify_cert = settings.getSetting('verify_cert') == 'true'
        log.debug("verify_cert: {0}", self.verify_cert)

    def post_capabilities(self):

        url = "{server}/emby/Sessions/Capabilities/Full?format=json"
        data = {
            'IconUrl': "https://raw.githubusercontent.com/faush01/plugin.video.embycon/develop/kodi.png",
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
        log.debug("Posted Capabilities: {0}", data)

    def get_item_playback_info(self, item_id, force_transcode):

        addon_settings = xbmcaddon.Addon()

        # ["hevc", "h265", "h264", "mpeg4", "msmpeg4v3", "mpeg2video", "vc1"]
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
            url = "{server}/emby/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s&EnableDirectPlay=false&EnableDirectStream=false" % (item_id, bitrate)
        else:
            url = "{server}/emby/Items/%s/PlaybackInfo?MaxStreamingBitrate=%s" % (item_id, bitrate)

        log.debug("PlaybackInfo : {0}", url)
        log.debug("PlaybackInfo : {0}", profile)
        play_info_result = self.download_url(url, post_body=playback_info, method="POST")
        play_info_result = json.loads(play_info_result)
        log.debug("PlaybackInfo : {0}", play_info_result)

        return play_info_result

    def get_item_playback_info_old(self, item_id):

        profile = {
            "Name": "Kodi",
            "MaxStreamingBitrate": 100000000,
            "MusicStreamingTranscodingBitrate": 1280000,
            "TimelineOffsetSeconds": 5,
            "TranscodingProfiles": [
                {
                    "Type": "Audio"
                },
                {
                    "Container": "m3u8",
                    "Type": "Video",
                    "AudioCodec": "aac,mp3,ac3,opus,flac,vorbis",
                    "VideoCodec": "h264,mpeg4,mpeg2video",
                    "MaxAudioChannels": "6"
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

        playback_info = {
            'UserId': self.get_user_id(),
            'DeviceProfile': profile,
            'AutoOpenLiveStream': True
        }

        url = "{server}/emby/Items/%s/PlaybackInfo" % item_id
        # url = "{server}/emby/Items/%s/PlaybackInfo?EnableDirectPlay=false&EnableDirectStream=false" % item_id
        log.debug("PlaybackInfo : {0}", url)
        log.debug("PlaybackInfo : {0}", profile)
        play_info_result = self.download_url(url, post_body=playback_info, method="POST")
        play_info_result = json.loads(play_info_result)
        log.debug("PlaybackInfo : {0}", play_info_result)

        return play_info_result

    def get_server(self):
        settings = xbmcaddon.Addon()
        host = settings.getSetting('ipaddress')

        if len(host) == 0 or host == "<none>":
            return None

        port = settings.getSetting('port')

        if not port and self.use_https:
            port = "443"
            settings.setSetting("port", port)
        elif not port:
            port = "80"
            settings.setSetting("port", port)

        # if user entered a full path i.e. http://some_host:port
        if host.lower().strip().startswith("http://") or host.lower().strip().startswith("https://"):
            log.debug("Extracting host info from url: {0}", host)
            url_bits = urlparse(host.strip())

            if host.lower().strip().startswith("http://"):
                settings.setSetting('protocol', '0')
                self.use_https = False
            elif host.lower().strip().startswith("https://"):
                settings.setSetting('protocol', '1')
                self.use_https = True

            if url_bits.hostname is not None and len(url_bits.hostname) > 0:
                host = url_bits.hostname

                if url_bits.username and url_bits.password:
                    host = "%s:%s@" % (url_bits.username, url_bits.password) + host

                settings.setSetting("ipaddress", host)

            if url_bits.port is not None and url_bits.port > 0:
                port = str(url_bits.port)
                settings.setSetting("port", port)

        if self.use_https:
            server = "https://" + host + ":" + port
        else:
            server = "http://" + host + ":" + port

        return server

    @staticmethod
    def get_all_artwork(item, server):
        all_art = defaultdict(lambda: "")

        item_id = item["Id"]
        item_type = item["Type"]
        image_tags = item["ImageTags"]
        # bg_item_tags = item["ParentBackdropImageTags"]

        # All the image tags
        for tag_name in image_tags:
            tag = image_tags[tag_name]
            art_url = "%s/emby/Items/%s/Images/%s/0?Format=original&Tag=%s" % (server, item_id, tag_name, tag)
            all_art[tag_name] = art_url

        # Series images
        if item_type in ["Episode", "Season"]:
            image_tag = item["SeriesPrimaryImageTag"]
            series_id = item["SeriesId"]
            if image_tag and series_id:
                art_url = "%s/emby/Items/%s/Images/Primary/0?Format=original&Tag=%s" % (server, series_id, image_tag)
                all_art["Primary.Series"] = art_url

        return all_art

    def get_artwork(self, data, art_type, parent=False, index=0, server=None):

        item_id = data["Id"]
        item_type = data["Type"]

        if item_type in ["Episode", "Season"]:
            if art_type != "Primary" or parent is True:
                item_id = data["SeriesId"]

        image_tag = ""
        # "e3ab56fe27d389446754d0fb04910a34" # a place holder tag, needs to be in this format

        # for episodes always use the parent BG
        if item_type == "Episode" and art_type == "Backdrop":
            item_id = data["ParentBackdropItemId"]
            bg_item_tags = data["ParentBackdropImageTags"]
            if bg_item_tags is not None and len(bg_item_tags) > 0:
                image_tag = bg_item_tags[0]
        elif art_type == "Backdrop" and parent is True:
            item_id = data["ParentBackdropItemId"]
            bg_item_tags = data["ParentBackdropImageTags"]
            if bg_item_tags is not None and len(bg_item_tags) > 0:
                image_tag = bg_item_tags[0]
        elif art_type == "Backdrop":
            bg_tags = data["BackdropImageTags"]
            if bg_tags is not None and len(bg_tags) > index:
                image_tag = bg_tags[index]
                # log.debug("Background Image Tag: {0}", imageTag)
        elif parent is False:
            image_tags = data["ImageTags"]
            if image_tags is not None:
                image_tag_type = image_tags[art_type]
                if image_tag_type is not None:
                    image_tag = image_tag_type
                    # log.debug("Image Tag: {0}", imageTag)
        elif parent is True:
            if (item_type == "Episode" or item_type == "Season") and art_type == 'Primary':
                tag_name = 'SeriesPrimaryImageTag'
                id_name = 'SeriesId'
            else:
                tag_name = 'Parent%sImageTag' % art_type
                id_name = 'Parent%sItemId' % art_type
            parent_image_id = data[id_name]
            parent_image_tag = data[tag_name]
            if parent_image_id is not None and parent_image_tag is not None:
                item_id = parent_image_id
                image_tag = parent_image_tag
                # log.debug("Parent Image Tag: {0}", imageTag)

        # ParentTag not passed for Banner and Art
        if not image_tag and not ((art_type == 'Banner' or art_type == 'Art') and parent is True):
            # log.debug("No Image Tag for request:{0} item:{1} parent:{2}", art_type, item_type, parent)
            return ""

        artwork = "%s/emby/Items/%s/Images/%s/%s?Format=original&Tag=%s" % (server, item_id, art_type, index, image_tag)

        if self.use_https and not self.verify_cert:
            artwork += "|verifypeer=false"

        # log.debug("getArtwork: request:{0} item:{1} parent:{2} link:{3}", art_type, item_type, parent, artwork)

        '''
        # do not return non-existing images
        if (    (art_type != "Backdrop" and imageTag == "") |
                (art_type == "Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) |
                (art_type == "Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)
                ):
            artwork = ''
        '''

        return artwork

    def image_url(self, item_id, art_type, index, width, height, image_tag, server):

        # test imageTag e3ab56fe27d389446754d0fb04910a34
        artwork = "%s/emby/Items/%s/Images/%s/%s?Format=original&Tag=%s" % (server, item_id, art_type, index, image_tag)
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

        artwork = "%s/emby/Users/%s/Images/%s?Format=original&tag=%s" % (server, user_id, item_type, tag)

        if self.use_https and not self.verify_cert:
            artwork += "|verifypeer=false"

        return artwork

    def get_user_id(self):

        window = HomeWindow()
        userid = window.get_property("userid")
        user_image = window.get_property("userimage")

        if userid and user_image:
            log.debug("EmbyCon DownloadUtils -> Returning saved UserID: {0}", userid)
            return userid

        settings = xbmcaddon.Addon()
        user_details = load_user_details(settings)
        user_name = user_details.get("username", "")

        if not user_name:
            return ""
        log.debug("Looking for user name: {0}", user_name)

        try:
            json_data = self.download_url("{server}/emby/Users/Public?format=json", suppress=True, authenticate=False)
        except Exception as msg:
            log.error("Get User unable to connect: {0}", msg)
            return ""

        log.debug("GETUSER_JSONDATA_01: {0}", json_data)

        try:
            result = json.loads(json_data)
        except Exception as e:
            log.debug("Could not load user data: {0}", e)
            return ""

        if result is None:
            return ""

        log.debug("GETUSER_JSONDATA_02: {0}", result)

        secure = False
        for user in result:
            if user.get("Name") == unicode(user_name, "utf-8"):
                userid = user.get("Id")
                user_image = self.get_user_artwork(user, 'Primary')
                log.debug("Username Found: {0}", user.get("Name"))
                if user.get("HasPassword", False):
                    secure = True
                    log.debug("Username Is Secure (HasPassword=True)")
                break

        if secure or not userid:
            auth_ok = self.authenticate()
            if auth_ok == "":
                xbmcgui.Dialog().notification(string_load(30316),
                                              string_load(30044),
                                              icon="special://home/addons/plugin.video.embycon/icon.png")
                return ""
            if not userid:
                userid = window.get_property("userid")

        if userid and not user_image:
            user_image = 'DefaultUser.png'

        if userid == "":
            xbmcgui.Dialog().notification(string_load(30316),
                                          string_load(30045),
                                          icon="special://home/addons/plugin.video.embycon/icon.png")

        log.debug("userid: {0}", userid)

        window.set_property("userid", userid)
        window.set_property("userimage", user_image)

        return userid

    def authenticate(self):

        window = HomeWindow()

        token = window.get_property("AccessToken")
        if token is not None and token != "":
            log.debug("EmbyCon DownloadUtils -> Returning saved AccessToken: {0}", token)
            return token

        settings = xbmcaddon.Addon()
        port = settings.getSetting("port")
        host = settings.getSetting("ipaddress")
        if host is None or host == "" or port is None or port == "":
            return ""

        url = "{server}/emby/Users/AuthenticateByName?format=json"

        user_details = load_user_details(settings)
        user_name = urllib.quote(user_details.get("username", ""))
        pwd_text = urllib.quote(user_details.get("password", ""))

        message_data = "username=" + user_name + "&pw=" + pwd_text

        resp = self.download_url(url, post_body=message_data, method="POST", suppress=True, authenticate=False)
        log.debug("AuthenticateByName: {0}", resp)

        access_token = None
        userid = None
        try:
            result = json.loads(resp)
            access_token = result.get("AccessToken")
            # userid = result["SessionInfo"].get("UserId")
            userid = result["User"].get("Id")
        except:
            pass

        if access_token is not None:
            log.debug("User Authenticated: {0}", access_token)
            log.debug("User Id: {0}", userid)
            window.set_property("AccessToken", access_token)
            window.set_property("userid", userid)
            # WINDOW.setProperty("userimage", "")

            self.post_capabilities()

            return access_token
        else:
            log.debug("User NOT Authenticated")
            window.set_property("AccessToken", "")
            window.set_property("userid", "")
            window.set_property("userimage", "")
            return ""

    def get_auth_header(self, authenticate=True):
        client_info = ClientInformation()
        txt_mac = client_info.get_device_id()
        version = client_info.get_version()
        client = client_info.get_client()

        settings = xbmcaddon.Addon()
        device_name = settings.getSetting('deviceName')
        # remove none ascii chars
        device_name = device_name.decode("ascii", errors='ignore')
        # remove some chars not valid for names
        device_name = device_name.replace("\"", "_")
        if len(device_name) == 0:
            device_name = "EmbyCon"

        headers = {}
        headers["Accept-encoding"] = "gzip"
        headers["Accept-Charset"] = "UTF-8,*"

        if authenticate is False:
            auth_string = "MediaBrowser Client=\"" + client + "\",Device=\"" + device_name + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            # headers["Authorization"] = authString
            headers['X-Emby-Authorization'] = auth_string
            return headers
        else:
            userid = self.get_user_id()
            auth_string = "MediaBrowser UserId=\"" + userid + "\",Client=\"" + client + "\",Device=\"" + device_name + "\",DeviceId=\"" + txt_mac + "\",Version=\"" + version + "\""
            # headers["Authorization"] = authString
            headers['X-Emby-Authorization'] = auth_string

            auth_token = self.authenticate()
            if auth_token != "":
                headers["X-MediaBrowser-Token"] = auth_token

            log.debug("EmbyCon Authentication Header: {0}", headers)
            return headers

    @timer
    def download_url(self, url, suppress=False, post_body=None, method="GET", authenticate=True, headers=None):
        log.debug("downloadUrl")

        return_data = "null"
        settings = xbmcaddon.Addon()
        user_details = load_user_details(settings)
        username = user_details.get("username", "")
        server = None

        http_timeout = int(settings.getSetting("http_timeout"))

        if authenticate and username == "":
            return return_data

        if settings.getSetting("suppressErrors") == "true":
            suppress = True

        log.debug("Before: {0}", url)

        if url.find("{server}") != -1:
            server = self.get_server()
            if server is None:
                return return_data
            url = url.replace("{server}", server)

        if url.find("{userid}") != -1:
            userid = self.get_user_id()
            if not userid:
                return return_data
            url = url.replace("{userid}", userid)

        if url.find("{ItemLimit}") != -1:
            show_x_filtered_items = settings.getSetting("show_x_filtered_items")
            url = url.replace("{ItemLimit}", show_x_filtered_items)

        if url.find("{field_filters}") != -1:
            filter_string = get_details_string()
            url = url.replace("{field_filters}", filter_string)

        if url.find("{random_movies}") != -1:
            home_window = HomeWindow()
            random_movies = home_window.get_property("random-movies")
            if not random_movies:
                return return_data
            url = url.replace("{random_movies}", random_movies)

        log.debug("After: {0}", url)
        conn = None

        try:

            url_bits = urlparse(url.strip())

            protocol = url_bits.scheme
            host_name = url_bits.hostname
            port = url_bits.port
            user_name = url_bits.username
            user_password = url_bits.password
            url_path = url_bits.path
            url_puery = url_bits.query

            if not host_name or host_name == "<none>":
                return return_data

            local_use_https = False
            if protocol.lower() == "https":
                local_use_https = True

            server = "%s:%s" % (host_name, port)
            url_path = url_path + "?" + url_puery

            if local_use_https and self.verify_cert:
                log.debug("Connection: HTTPS, Cert checked")
                conn = httplib.HTTPSConnection(server, timeout=http_timeout)
            elif local_use_https and not self.verify_cert:
                log.debug("Connection: HTTPS, Cert NOT checked")
                conn = httplib.HTTPSConnection(server, timeout=http_timeout, context=ssl._create_unverified_context())
            else:
                log.debug("Connection: HTTP")
                conn = httplib.HTTPConnection(server, timeout=http_timeout)

            head = self.get_auth_header(authenticate)

            if user_name and user_password:
                # add basic auth headers
                user_and_pass = b64encode(b"%s:%s" % (user_name, user_password)).decode("ascii")
                head["Authorization"] = 'Basic %s' % user_and_pass

            head["User-Agent"] = "EmbyCon-" + ClientInformation().get_version()
            log.debug("HEADERS: {0}", head)

            if post_body is not None:
                if isinstance(post_body, dict):
                    content_type = "application/json"
                    post_body = json.dumps(post_body)
                else:
                    content_type = "application/x-www-form-urlencoded"

                head["Content-Type"] = content_type
                log.debug("Content-Type: {0}", content_type)

                log.debug("POST DATA: {0}", post_body)
                conn.request(method=method, url=url_path, body=post_body, headers=head)
            else:
                conn.request(method=method, url=url_path, headers=head)

            data = conn.getresponse()
            log.debug("HTTP response: {0} {1}", data.status, data.reason)
            log.debug("GET URL HEADERS: {0}", data.getheaders())

            if int(data.status) == 200:
                ret_data = data.read()
                content_type = data.getheader('content-encoding')
                log.debug("Data Len Before: {0}", len(ret_data))
                if content_type == "gzip":
                    ret_data = StringIO.StringIO(ret_data)
                    gzipper = gzip.GzipFile(fileobj=ret_data)
                    return_data = gzipper.read()
                else:
                    return_data = ret_data
                if headers is not None and isinstance(headers, dict):
                    headers.update(data.getheaders())
                log.debug("Data Len After: {0}", len(return_data))
                log.debug("====== 200 returned =======")
                log.debug("Content-Type: {0}", content_type)
                log.debug("{0}", return_data)
                log.debug("====== 200 finished ======")

            elif int(data.status) >= 400:

                if int(data.status) == 401:
                    # remove any saved password
                    m = hashlib.md5()
                    m.update(username)
                    hashed_username = m.hexdigest()
                    log.error("HTTP response error 401 auth error, removing any saved passwords for user: {0}", hashed_username)
                    settings.setSetting("saved_user_password_" + hashed_username, "")
                    save_user_details(settings, "", "")

                log.error("HTTP response error: {0} {1}", data.status, data.reason)
                if suppress is False:
                    xbmcgui.Dialog().notification(string_load(30316),
                                                  string_load(30200) % str(data.reason),
                                                  icon="special://home/addons/plugin.video.embycon/icon.png")

        except Exception as msg:
            log.error("Unable to connect to {0} : {1}", server, msg)
            if suppress is False:
                xbmcgui.Dialog().notification(string_load(30316),
                                              str(msg),
                                              icon="special://home/addons/plugin.video.embycon/icon.png")

        finally:
            try:
                log.debug("Closing HTTP connection: {0}", conn)
                conn.close()
            except:
                pass

        return return_data
