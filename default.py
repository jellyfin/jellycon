# Gnu General Public License - see LICENSE.TXT

import xbmcaddon

from resources.lib.simple_logging import SimpleLogging
from resources.lib.functions import mainEntryPoint
from resources.lib.tracking import set_timing_enabled

log = SimpleLogging('default')

settings = xbmcaddon.Addon()
log_timing_data = settings.getSetting('log_timing') == "true"
if log_timing_data:
    set_timing_enabled(True)

log.debug("About to enter mainEntryPoint()")

mainEntryPoint()

# clear done and exit.
# sys.modules.clear()
