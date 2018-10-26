import encodings
import xbmcaddon
from simple_logging import SimpleLogging

log = SimpleLogging(__name__)
addon = xbmcaddon.Addon()


def string_load(string_id):
    try:
        return addon.getLocalizedString(string_id).encode('utf-8', 'ignore')
    except Exception as e:
        log.error('Failed String Load: {0} ({1})', string_id, e)
        return str(string_id)

