# Gnu General Public License - see LICENSE.TXT

import xbmc
import xbmcgui
import xbmcaddon

from datetime import timedelta
import time
import json
import hashlib

from simple_logging import SimpleLogging
from downloadutils import DownloadUtils
from resume_dialog import ResumeDialog
from utils import PlayUtils, getArt, id_generator
from kodi_utils import HomeWindow
from translation import i18n
from json_rpc import json_rpc

log = SimpleLogging(__name__)
downloadUtils = DownloadUtils()


def playFile(play_info):

    id = play_info.get("item_id")
    auto_resume = play_info.get("auto_resume", "-1")
    force_transcode = play_info.get("force_transcode", False)
    media_source_id = play_info.get("media_source_id", "")
    use_default = play_info.get("use_default", False)

    log.debug("playFile id(%s) resume(%s) force_transcode(%s)" % (id, auto_resume, force_transcode))

    settings = xbmcaddon.Addon('plugin.video.embycon')
    addon_path = settings.getAddonInfo('path')
    jump_back_amount = int(settings.getSetting("jump_back_amount"))

    server = downloadUtils.getServer()

    url = "{server}/emby/Users/{userid}/Items/" + id + "?format=json"
    jsonData = downloadUtils.downloadUrl(url, suppress=False, popup=1)
    result = json.loads(jsonData)
    log.debug("Playfile item info: " + str(result))

    # select the media source to use
    media_sources = result.get('MediaSources')
    selected_media_source = None

    if media_sources is None or len(media_sources) == 0:
        log.debug("Play Failed! There is no MediaSources data!")
        return

    elif len(media_sources) == 1:
        selected_media_source = media_sources[0]

    elif media_source_id != "":
        for source in media_sources:
            if source.get("Id", "na") == media_source_id:
                selected_media_source = source
                break

    elif len(media_sources) > 1:
        sourceNames = []
        for source in media_sources:
            sourceNames.append(source.get("Name", "na"))

        dialog = xbmcgui.Dialog()
        resp = dialog.select(i18n('select_source'), sourceNames)
        if resp > -1:
            selected_media_source = media_sources[resp]
        else:
            log.debug("Play Aborted, user did not select a MediaSource")
            return

    if selected_media_source is None:
        log.debug("Play Aborted, MediaSource was None")
        return

    seekTime = 0
    auto_resume = int(auto_resume)

    # process user data for resume points
    if auto_resume != -1:
        seekTime = (auto_resume / 1000) / 10000
    else:
        userData = result.get("UserData")
        if userData.get("PlaybackPositionTicks") != 0:

            reasonableTicks = int(userData.get("PlaybackPositionTicks")) / 1000
            seekTime = reasonableTicks / 10000
            displayTime = str(timedelta(seconds=seekTime))

            resumeDialog = ResumeDialog("ResumeDialog.xml", addon_path, "default", "720p")
            resumeDialog.setResumeTime("Resume from " + displayTime)
            resumeDialog.doModal()
            resume_result = resumeDialog.getResumeAction()
            del resumeDialog
            log.debug("Resume Dialog Result: " + str(resume_result))

            # check system settings for play action
            # if prompt is set ask to set it to auto resume
            params = {"setting": "myvideos.selectaction"}
            setting_result = json_rpc('Settings.getSettingValue').execute(params)
            log.debug("Current Setting (myvideos.selectaction): %s" % setting_result)
            current_value = setting_result.get("result", None)
            if current_value is not None:
                current_value = current_value.get("value", -1)
            if current_value not in (2,3):
                return_value = xbmcgui.Dialog().yesno(i18n('extra_prompt'), i18n('turn_on_auto_resume?'))
                if return_value:
                    params = {"setting": "myvideos.selectaction", "value": 2}
                    json_rpc_result = json_rpc('Settings.setSettingValue').execute(params)
                    log.debug("Save Setting (myvideos.selectaction): %s" % json_rpc_result)

            if resume_result == 1:
                seekTime = 0
            elif resume_result == -1:
                return

    listitem_props = []
    playback_type = "0"
    playurl = None
    play_session_id = id_generator()
    log.debug("play_session_id: %s" % play_session_id)

    # check if strm file, path will contain contain strm contents
    if selected_media_source.get('Container') == 'strm':
        playurl, listitem_props = PlayUtils().getStrmDetails(selected_media_source)
        if playurl is None:
            return

    if not playurl:
        playurl, playback_type = PlayUtils().getPlayUrl(id, selected_media_source, force_transcode, play_session_id)

    log.debug("Play URL: " + str(playurl) + " ListItem Properties: " + str(listitem_props))

    playback_type_string = "DirectPlay"
    if playback_type == "2":
        playback_type_string = "Transcode"
    elif playback_type == "1":
        playback_type_string = "DirectStream"

    home_window = HomeWindow()
    home_window.setProperty("PlaybackType_" + id, playback_type_string)
    home_window.setProperty("PlaySessionId_" + id, play_session_id)

    # add the playback type into the overview
    if result.get("Overview", None) is not None:
        result["Overview"] = playback_type_string + "\n" + result.get("Overview")
    else:
        result["Overview"] = playback_type_string

    # add title decoration is needed
    item_title = result.get("Name", i18n('missing_title'))
    add_episode_number = settings.getSetting('addEpisodeNumber') == 'true'
    if result.get("Type") == "Episode" and add_episode_number:
        episode_num = result.get("IndexNumber")
        if episode_num is not None:
            if episode_num < 10:
                episode_num = "0" + str(episode_num)
            else:
                episode_num = str(episode_num)
        else:
            episode_num = ""
        item_title =  episode_num + " - " + item_title

    list_item = xbmcgui.ListItem(label=item_title)

    if playback_type == "2": # if transcoding then prompt for audio and subtitle
        playurl = audioSubsPref(playurl, list_item, selected_media_source, id, use_default)
        log.debug("New playurl for transcoding : " + playurl)

    elif playback_type == "1": # for direct stream add any streamable subtitles
        externalSubs(selected_media_source, list_item, id)

    list_item.setPath(playurl)
    list_item = setListItemProps(id, list_item, result, server, listitem_props, item_title)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    playlist.add(playurl, list_item)
    xbmc.Player().play(playlist)

    if seekTime == 0:
        return

    count = 0
    while not xbmc.Player().isPlaying():
        log.debug("Not playing yet...sleep for 1 sec")
        count = count + 1
        if count >= 10:
            return
        else:
            xbmc.Monitor().waitForAbort(1)

    seekTime = seekTime - jump_back_amount

    while xbmc.Player().getTime() < (seekTime - 5):
        # xbmc.Player().pause()
        xbmc.sleep(100)
        xbmc.Player().seekTime(seekTime)
        xbmc.sleep(100)
        # xbmc.Player().play()

def setListItemProps(id, listItem, result, server, extra_props, title):
    # set up item and item info
    thumbID = id
    eppNum = -1
    seasonNum = -1

    art = getArt(result, server=server)
    listItem.setIconImage(art['thumb'])  # back compat
    listItem.setProperty('fanart_image', art['fanart'])  # back compat
    listItem.setProperty('discart', art['discart'])  # not avail to setArt
    listItem.setArt(art)

    listItem.setProperty('IsPlayable', 'true')
    listItem.setProperty('IsFolder', 'false')
    listItem.setProperty('id', result.get("Id"))

    for prop in extra_props:
        listItem.setProperty(prop[0], prop[1])

    # play info
    details = {
        'title': title,
        'plot': result.get("Overview")
    }

    if (eppNum > -1):
        details["episode"] = str(eppNum)

    if (seasonNum > -1):
        details["season"] = str(seasonNum)

    listItem.setInfo("Video", infoLabels=details)

    return listItem

# For transcoding only
# Present the list of audio and subtitles to select from
# for external streamable subtitles add the URL to the Kodi item and let Kodi handle it
# else ask for the subtitles to be burnt in when transcoding
def audioSubsPref(url, list_item, media_source, item_id, use_default):

    dialog = xbmcgui.Dialog()
    audioStreamsList = {}
    audioStreams = []
    audioStreamsChannelsList = {}
    subtitleStreamsList = {}
    subtitleStreams = ['No subtitles']
    downloadableStreams = []
    selectAudioIndex = ""
    selectSubsIndex = ""
    playurlprefs = "%s" % url
    default_audio = media_source.get('DefaultAudioStreamIndex', 1)
    default_sub = media_source.get('DefaultSubtitleStreamIndex', "")

    media_streams = media_source['MediaStreams']

    for stream in media_streams:
        # Since Emby returns all possible tracks together, have to sort them.
        index = stream['Index']

        if 'Audio' in stream['Type']:
            codec = stream['Codec']
            channelLayout = stream.get('ChannelLayout', "")

            try:
                track = "%s - %s - %s %s" % (index, stream['Language'], codec, channelLayout)
            except:
                track = "%s - %s %s" % (index, codec, channelLayout)

            audioStreamsChannelsList[index] = stream['Channels']
            audioStreamsList[track] = index
            audioStreams.append(track)

        elif 'Subtitle' in stream['Type']:
            try:
                track = "%s - %s" % (index, stream['Language'])
            except:
                track = "%s - %s" % (index, stream['Codec'])

            default = stream['IsDefault']
            forced = stream['IsForced']
            downloadable = stream['IsTextSubtitleStream'] and stream['IsExternal'] and stream['SupportsExternalStream']

            if default:
                track = "%s - Default" % track
            if forced:
                track = "%s - Forced" % track
            if downloadable:
                downloadableStreams.append(index)

            subtitleStreamsList[track] = index
            subtitleStreams.append(track)

    if use_default:
        playurlprefs += "&AudioStreamIndex=%s" % default_audio

    elif len(audioStreams) > 1:
        resp = dialog.select(i18n('select_audio_stream'), audioStreams)
        if resp > -1:
            # User selected audio
            selected = audioStreams[resp]
            selectAudioIndex = audioStreamsList[selected]
            playurlprefs += "&AudioStreamIndex=%s" % selectAudioIndex
        else:  # User backed out of selection
            playurlprefs += "&AudioStreamIndex=%s" % default_audio

    else:  # There's only one audiotrack.
        selectAudioIndex = audioStreamsList[audioStreams[0]]
        playurlprefs += "&AudioStreamIndex=%s" % selectAudioIndex

    if len(subtitleStreams) > 1:
        if use_default:
            playurlprefs += "&SubtitleStreamIndex=%s" % default_sub

        else:
            resp = dialog.select(i18n('select_subtitle'), subtitleStreams)
            if resp == 0:
                # User selected no subtitles
                pass
            elif resp > -1:
                # User selected subtitles
                selected = subtitleStreams[resp]
                selectSubsIndex = subtitleStreamsList[selected]

                # Load subtitles in the listitem if downloadable
                if selectSubsIndex in downloadableStreams:
                    url = [("%s/Videos/%s/%s/Subtitles/%s/Stream.srt"
                            % (downloadUtils.getServer(), item_id, item_id, selectSubsIndex))]
                    log.debug("Streaming subtitles url: %s %s" % (selectSubsIndex, url))
                    list_item.setSubtitles(url)
                else:
                    # Burn subtitles
                    playurlprefs += "&SubtitleStreamIndex=%s" % selectSubsIndex

            else:  # User backed out of selection
                playurlprefs += "&SubtitleStreamIndex=%s" % default_sub

    # Get number of channels for selected audio track
    audioChannels = audioStreamsChannelsList.get(selectAudioIndex, 0)
    if audioChannels > 2:
        playurlprefs += "&AudioBitrate=384000"
    else:
        playurlprefs += "&AudioBitrate=192000"

    return playurlprefs

# direct stream, set any available subtitle streams
def externalSubs(media_source, list_item, item_id):

    externalsubs = []
    media_streams = media_source['MediaStreams']

    for stream in media_streams:

        if (stream['Type'] == "Subtitle"
                and stream['IsExternal']
                and stream['IsTextSubtitleStream']
                and stream['SupportsExternalStream']):

            index = stream['Index']
            url = ("%s/Videos/%s/%s/Subtitles/%s/Stream.%s"
                   % (downloadUtils.getServer(), item_id, item_id, index, stream['Codec']))

            externalsubs.append(url)

    list_item.setSubtitles(externalsubs)