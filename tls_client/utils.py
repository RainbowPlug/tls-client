from sys import platform
from platform import machine
import ctypes


def get_dependency_filename():
    if platform == 'darwin':
        file_ext = '-arm64.dylib' if machine() == "arm64" else '-x86.dylib'
    elif platform in ('win32', 'cygwin'):
        file_ext = '-64.dll' if 8 == ctypes.sizeof(ctypes.c_voidp) else '-32.dll'
    else:
        if machine() == "aarch64":
            file_ext = '-arm64.so'
        # EXACT match, not a substring test. `"x86" in machine()` is True on
        # every normal 64-bit Linux box, because platform.machine() returns
        # "x86_64" there and "x86" is a substring of it. That loaded the 32-bit
        # object on amd64 and died at import with
        #   OSError: ... wrong ELF class: ELFCLASS32
        # while the correct tls-client-amd64.so sat in the same directory. It
        # takes down every process that imports tls_client, on its next restart
        # rather than immediately, so it presents as an unrelated mass outage.
        # A v1.4 regression; v1.3 did not have it. bet337's prod box has been
        # carrying a hand-applied hot patch for this since 2026-08-11, which any
        # `pip install -r requirements.txt` silently reverts. This is that fix,
        # made durable so the 152 upgrade does not re-break the box it ships to.
        elif machine() in ("i386", "i686", "x86"):
            file_ext = '-x86.so'
        else:
            file_ext = '-amd64.so'

    return f'tls-client{file_ext}'
