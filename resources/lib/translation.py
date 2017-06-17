import xbmcaddon
from simple_logging import SimpleLogging

log = SimpleLogging(__name__)
addon = xbmcaddon.Addon(id='plugin.video.embycon')


def i18n(string_id):
    try:
        return addon.getLocalizedString(STRINGS[string_id]).encode('utf-8', 'ignore')
    except Exception as e:
        log.error('Failed String Lookup: %s (%s)' % (string_id, e))
        return string_id


STRINGS = {
    'server_port:': 30001,
    'username:': 30005,
    'password:': 30006,
    'incorrect_user_pass': 30044,
    'username_not_found': 30045,
    'deleting': 30052,
    'waiting_server_delete': 30053,
    'username_secured': 30060,
    'username_userdefined': 30061,
    'username_userinput': 30062,
    'n/a': 30063,
    'confirm_file_delete': 30091,
    'file_delete_confirm': 30092,
    'loading_content': 30112,
    'retrieving_data': 30113,
    'done': 30125,
    'processing_item:': 30126,
    'error': 30135,
    'service_not_running': 30136,
    'restart_kodi': 30137,
    'no_media_type': 30139,
    'select_server': 30166,
    'server_detect_succeeded': 30167,
    'found_server': 30168,
    'address:': 30169,
    'select_user': 30180,
    'url_error_': 30200,
    'unable_connect_server': 30201,
    'tvshows': 30229,
    'default_view': 30230,
    'movies': 30231,
    'boxsets': 30232,
    'series': 30233,
    'seasons': 30234,
    'episodes': 30235,
    'save': 30236,
    'start_from_beginning': 30237,
    'default_sort': 30238,
    'next_page': 30245,
    'search': 30246,
    'widgets': 30247,
    'emby_movies': 30248,
    'emby_tvshows': 30249,
    'unknown': 30250,
    'movies_genre': 30251,
    'movies_az': 30252,
    'change_user': 30253,
    'show_settings': 30254,
    'set_default_views': 30255,
    'movies_all': 30256,
    'movies_recently_added': 30257,
    'movies_in_progress': 30258,
    'movies_favorites': 30259,
    'movies_boxsets': 30260,
    'tvshows_all': 30261,
    'tvshows_favorites': 30262,
    'episodes_recently_added': 30263,
    'episodes_in_progress': 30264,
    'episodes_up_next': 30265,
    'upcoming_tv': 30266,
    '_in_progress': 30267,
    '_recently_added': 30268,
    'movies_random': 30269,
    'emby_mark_watched': 30270,
    'emby_mark_unwatched': 30271,
    'emby_set_favorite': 30272,
    'emby_unset_favorite': 30273,
    'emby_delete': 30274,
    'missing_title': 30280,
    'emby_force_transcode': 30275,
    'extra_prompt': 30276,
    'turn_on_auto_resume?': 30277,
}
