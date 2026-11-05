#!/usr/bin/env python3
"""Read-only Landlock ABI query, limited to the workflow's Linux x86_64 platform."""
import ctypes
import json
import os
import platform

MINIMUM_ABI = 8


def query_abi():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Landlock ABI query requires Linux x86_64')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    # Linux x86_64 syscall table:444; LANDLOCK_CREATE_RULESET_VERSION:1.
    # Null attributes/zero size query the ABI without creating a ruleset.
    abi = int(libc.syscall(ctypes.c_long(444), ctypes.c_void_p(), ctypes.c_size_t(0), ctypes.c_uint(1)))
    if abi < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return abi


def require_abi(abi):
    if type(abi) is not int or abi < MINIMUM_ABI:
        raise RuntimeError('Landlock ABI must be at least8; got ' + str(abi))


def main():
    abi = query_abi()
    print('LANDLOCK_ABI ' + json.dumps({'abi': abi, 'minimum_required': MINIMUM_ABI,
          'platform': 'Linux x86_64', 'syscall': 444, 'version_query_flag': 1}), flush=True)
    require_abi(abi)
    print('LANDLOCK_ABI_ACCEPTED', flush=True)


if __name__ == '__main__':
    main()
