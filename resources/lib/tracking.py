from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import sys
import functools
import time

from .lazylogger import LazyLogger

log = LazyLogger(__name__)

enabled = False


def set_timing_enabled(val):
    global enabled
    enabled = val


def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        started = time.time()
        value = func(*args, **kwargs)
        ended = time.time()
        if enabled:
            data = ""
            if func.__name__ == "download_url" and len(args) > 1:
                data = args[1]
            elif func.__name__ == "main_entry_point" and len(sys.argv) > 2:
                data = sys.argv[2]
            log.info("timing_data|{0}|{1}|{2}|{3}".format(
                func.__name__, started, ended, data)
            )
        return value
    return wrapper
