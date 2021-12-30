# https://github.com/ilastik/lazyflow/blob/master/lazyflow/utility/fileLock.py
###############################################################################
#   lazyflow: data flow based lazy parallel computation framework
#
#       Copyright (C) 2011-2014, the ilastik developers
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the Lesser GNU General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# See the files LICENSE.lgpl2 and LICENSE.lgpl3 for full text of the
# GNU Lesser General Public License version 2.1 and 3 respectively.
# This information is also available on the ilastik web site at:
# 		   http://ilastik.org/license/
###############################################################################
"""
Implementation of a simple cross-platform file locking mechanism.
This is a modified version of code retrieved on 2013-01-01 from
http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python.
(The original code was released under the BSD License.  See below for details.)

Modifications in this version:
 - Tweak docstrings for sphinx.
 - Accept an absolute path for the protected file (instead of a file name relative to cwd).
 - Allow timeout to be None.
 - Fixed a bug that caused the original code to be NON-threadsafe when the same FileLock instance was shared by multiple threads in one process.
   (The original was safe for multiple processes, but not multiple threads in a single process.  This version is safe for both cases.)
 - Added ``purge()`` function.
 - Added ``available()`` function.
 - Expanded API to mimic ``threading.Lock interface``:
   - ``__enter__`` always calls ``acquire()``, and therefore blocks if ``acquire()`` was called previously.
   - ``__exit__`` always calls ``release()``.  It is therefore a bug to call ``release()`` from within a context manager.
   - Added ``locked()`` function.
   - Added blocking parameter to ``acquire()`` method

WARNINGS:
 - The locking mechanism used here may need to be changed to support old NFS filesystems:
   http://lwn.net/Articles/251004
   (Newer versions of NFS should be okay, e.g. NFSv3 with Linux kernel 2.6. Check the open(2) man page for details about O_EXCL.)
 - This code has not been thoroughly tested on Windows, and there has been one report of incorrect results on Windows XP and Windows 7.
   The locking mechanism used in this class should (in theory) be cross-platform, but use at your own risk.

ORIGINAL LICENSE:

The original code did not properly include license text.
(It merely said "License: BSD".)
Therefore, we'll attach the following generic BSD License terms to this file.
Those who extract this file from the lazyflow code base (LGPL) for their own use
are therefore bound by the terms of both the Simplified BSD License below AND the LGPL.

Copyright (c) 2013, Evan Fosmark and others.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.
"""

# from builtins import object

import os
import sys
import time
import errno


class FileLock(object):
    """ A file locking mechanism that has context-manager support so
        you can use it in a ``with`` statement. This should be relatively cross
        compatible as it doesn't rely on ``msvcrt`` or ``fcntl`` for the locking.
    """

    class FileLockException(Exception):
        pass

    def __init__(self, protected_file_path, timeout=None, delay=1, lock_file_contents=None):
        """ Prepare the file locker. Specify the file to lock and optionally
            the maximum timeout and the delay between each attempt to lock.
        """
        self.is_locked = False
        self.lockfile = protected_file_path + ".lock"
        self.timeout = timeout
        self.delay = delay
        self._lock_file_contents = lock_file_contents
        if self._lock_file_contents is None:
            self._lock_file_contents = "Owning process args:\n"
            for arg in sys.argv:
                self._lock_file_contents += arg + "\n"

    def locked(self):
        """
        Returns True iff the file is owned by THIS FileLock instance.
        (Even if this returns false, the file could be owned by another FileLock instance, possibly in a different thread or process).
        """
        return self.is_locked

    def available(self):
        """
        Returns True iff the file is currently available to be locked.
        """
        return not os.path.exists(self.lockfile)

    def acquire(self, blocking=True):
        """ Acquire the lock, if possible. If the lock is in use, and `blocking` is False, return False.
            Otherwise, check again every `self.delay` seconds until it either gets the lock or
            exceeds `timeout` number of seconds, in which case it raises an exception.
        """
        start_time = time.time()
        while True:
            try:
                # Attempt to create the lockfile.
                # These flags cause os.open to raise an OSError if the file already exists.
                fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                with os.fdopen(fd, "a") as f:
                    # Print some info about the current process as debug info for anyone who bothers to look.
                    f.write(self._lock_file_contents)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                if self.timeout is not None and (time.time() - start_time) >= self.timeout:
                    raise FileLock.FileLockException("Timeout occurred.")
                if not blocking:
                    return False
                time.sleep(self.delay)
        self.is_locked = True
        return True

    def release(self):
        """ Get rid of the lock by deleting the lockfile.
            When working in a `with` statement, this gets automatically
            called at the end.
        """
        self.is_locked = False
        os.unlink(self.lockfile)

    def __enter__(self):
        """ Activated when used in the with statement.
            Should automatically acquire a lock to be used in the with block.
        """
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        """ Activated at the end of the with statement.
            It automatically releases the lock if it isn't locked.
        """
        self.release()

    def __del__(self):
        """ Make sure this ``FileLock`` instance doesn't leave a .lock file
            lying around.
        """
        if self.is_locked:
            self.release()

    def purge(self):
        """
        For debug purposes only.  Removes the lock file from the hard disk.
        """
        if os.path.exists(self.lockfile):
            self.release()
            return True
        return False


"""
if __name__ == "__main__":
    import sys
    import functools
    import threading
    import tempfile
    from builtins import range


    temp_dir = tempfile.mkdtemp()
    protected_filepath = os.path.join(temp_dir, "somefile.txt")
    print("Protecting file: {}".format(protected_filepath))
    fl = FileLock(protected_filepath)

    def writeLines(line, repeat=10):
        with fl:
            for _ in range(repeat):
                with open(protected_filepath, "a") as f:
                    f.write(line + "\n")
                    f.flush()

    th1 = threading.Thread(target=functools.partial(writeLines, "1111111111111111111111111111111"))
    th2 = threading.Thread(target=functools.partial(writeLines, "2222222222222222222222222222222"))
    th3 = threading.Thread(target=functools.partial(writeLines, "3333333333333333333333333333333"))
    th4 = threading.Thread(target=functools.partial(writeLines, "4444444444444444444444444444444"))

    th1.start()
    th2.start()
    th3.start()
    th4.start()

    th1.join()
    th2.join()
    th3.join()
    th4.join()

    assert not os.path.exists(fl.lockfile), "The lock file wasn't cleaned up!"

    # Print the contents of the file.
    # Please manually inspect the output.  Does it look like the operations were atomic?
    with open(protected_filepath, "r") as f:
        sys.stdout.write(f.read())
"""
