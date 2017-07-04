# Gnu General Public License - see LICENSE.TXT

from resources.lib.simple_logging import SimpleLogging
from resources.lib.functions import mainEntryPoint
from resources.lib.ga_client import GoogleAnalytics, log_error

log = SimpleLogging('default')

log.info("About to enter mainEntryPoint()")

try:
    mainEntryPoint()
except Exception as error:
    ga = GoogleAnalytics()
    err_strings = ga.formatException()
    ga.sendEventData("Exception", err_strings[0], err_strings[1])
    log.error(error)
    raise

# clear done and exit.
# sys.modules.clear()
