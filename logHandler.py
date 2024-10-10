from datetime import datetime
from pytz import timezone
import logging

def timetz(*args):
    return datetime.now(tz).timetuple()

tz = timezone('America/New_York')
# tz = timezone('Asia/Shanghai') # UTC, Asia/Shanghai, Europe/Berlin

logging.Formatter.converter = timetz

logLevel = logging.DEBUG

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logLevel,
    datefmt="%m-%d %H:%M:%S",
    filename="log.log",
    filemode="w"
)

logger = logging.getLogger(__name__)


logger.debug('Test Logger Debug - too much information')
logger.info('Test Logger Info - just some usual stuff')
logger.warning('Test Logger Warning - just more useful information')
logger.error('Test Logger Error - now something needs fixing')
