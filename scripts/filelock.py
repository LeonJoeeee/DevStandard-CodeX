"""One advisory exclusive lock over an open file descriptor, per platform.

Unix keeps `fcntl.flock`; Windows uses `msvcrt.locking` on the first byte. Both are
non-blocking: a competing lock reports busy so callers refuse instead of waiting.
The kernel releases the lock when the descriptor closes, including on process exit.
"""
import errno
import os

if os.name == 'nt':  # pragma: no cover - exercised on Windows only
    import msvcrt

    _BUSY = {errno.EACCES, errno.EAGAIN, errno.EDEADLK,
             getattr(errno, 'EDEADLOCK', errno.EDEADLK)}

    def try_lock(fd):
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError as error:
            if error.errno in _BUSY:
                return False
            raise
else:
    import fcntl

    def try_lock(fd):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
