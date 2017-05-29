# Gnu General Public License - see LICENSE.TXT

from resources.lib.simple_logging import SimpleLogging
from resources.lib.functions import mainEntryPoint

log = SimpleLogging('default')

log.info("About to enter mainEntryPoint()")

mainEntryPoint()

# clear done and exit.
# sys.modules.clear()
