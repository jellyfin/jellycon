# -*- coding: utf-8 -*-

import logging
import xbmc

def config(level):

    logger = logging.getLogger('EmbyCon')
    handler = LogHandler(level)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

class LogHandler(logging.StreamHandler):

    cutoff_level = 0
    
    def __init__(self, level):

        self.cutoff_level = level
        xbmc.log("EmbyCon -> Setting Log Level: " + str(self.cutoff_level))
        logging.StreamHandler.__init__(self)
        self.setFormatter(MyFormatter())

    def emit(self, record):

        if self._get_log_level(record.levelno, self.cutoff_level):
            try:
                xbmc.log(self.format(record), level=xbmc.LOGNOTICE)
            except UnicodeEncodeError:
                xbmc.log(self.format(record).encode('utf-8'), level=xbmc.LOGNOTICE)

    @classmethod
    def _get_log_level(cls, level, cutoff_level):

        levels = {
            logging.ERROR: 0,
            logging.WARNING: 1,
            logging.INFO: 1,
            logging.DEBUG: 2
        }
        try:
            log_level = int(cutoff_level)
        except ValueError as e:
            xbmc.log("Error setting log level: " + str(cutoff_level))
            log_level = 0

        return log_level >= levels[level]

class MyFormatter(logging.Formatter):

    def __init__(self, fmt="%(name)s -> %(message)s"):

        logging.Formatter.__init__(self, fmt)

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._fmt

        # Replace the original format with one customized by logging level
        if record.levelno in (logging.DEBUG, logging.ERROR):
            self._fmt = '%(name)s -> %(levelname)s: %(message)s'

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._fmt = format_orig

        return result
