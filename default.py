# Gnu General Public License - see LICENSE.TXT

import xbmcaddon

from resources.lib.lazylogger import LazyLogger
from resources.lib.functions import main_entry_point
from resources.lib.tracking import set_timing_enabled

log = LazyLogger('default')

settings = xbmcaddon.Addon()
log_timing_data = settings.getSetting('log_timing') == "true"
if log_timing_data:
    set_timing_enabled(True)

log.debug("About to enter mainEntryPoint()")

main_entry_point()
