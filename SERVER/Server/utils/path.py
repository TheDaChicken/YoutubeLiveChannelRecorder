"""
Basically from https://stackoverflow.com/a/34102855
"""
import sys
import errno
import os

ERROR_INVALID_NAME = 123


def check_path_creatable(pathname: str) -> bool:
    dirname = os.path.dirname(pathname) or os.getcwd()
    return os.access(dirname, os.W_OK)


def is_pathname_valid(pathname: str) -> bool:
    if not isinstance(pathname, str) or not pathname:
        return False
    _, pathname = os.path.splitdrive(pathname)
    root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
        if sys.platform == 'win32' else os.path.sep
    assert os.path.isdir(root_dirname)

    try:
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    except TypeError:
        return False
    else:
        return True
