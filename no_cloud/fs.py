# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import os
import yaml
import stat

from .crypto import fernet_decrypt
from .utils import get_password, nth, ignored, cleanup_path

DEFAULT_MODE = 0600


def is_encrypted(filename):
    return filename.endswith('.crypt')


def load_configuration(filename, version=0):
    with open(filename, 'rb') as file:
        data = file.read()

    if is_encrypted(filename):
        password = get_password('Decryption password', confirm=False)
        data = fernet_decrypt(data, password)

    data = yaml.load_all(data)

    if version >= 0:
        data = nth(data, version)

    return data


def find_in_path(root, *candidates):
    if os.path.isfile(root):
        root = os.path.dirname(root)

    for candidate in candidates:
        if os.path.isfile(root + '/' + candidate):
            return root, candidate

    if root == '/':
        return None, None

    return find_in_path(os.path.dirname(root), *candidates)


def list_files(root):
    if type(root) in (list, tuple):
        for item in root:
            for filename in list_files(item):
                yield filename
    elif os.path.isfile(root):
        yield os.path.abspath(root)
    else:
        for path, junk, filenames in os.walk(root):
            for filename in filenames:
                if ignored(filename):
                    continue

                yield cleanup_path(path + '/' + filename, keep_leading=True)


def test_mode(filename, expected_mode=DEFAULT_MODE):
    mode = os.stat(filename).st_mode
    return stat.S_IMODE(mode) == expected_mode


def fix_mode(filename, expected_mode=DEFAULT_MODE):
    os.chmod(filename, expected_mode)
