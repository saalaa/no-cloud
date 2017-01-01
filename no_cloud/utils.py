# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import re
import fnmatch
import getpass
import pyperclip

TIME_UNITS = {
    'm': 60,
    'h': 60 * 60,
    'd': 60 * 60 * 24,
    'w': 60 * 60 * 24 * 7
}


def human_timedelta(time):
    match = re.match('^(\d+)([mhdw])$', time)

    assert match, 'unknown time format `%s`' % time

    value = match.group(1)
    unit = match.group(2)

    return int(value) * TIME_UNITS[unit]


def get_password(prompt='Password', confirm=False):
    password = getpass.getpass(prompt + ': ')

    if confirm:
        confirmation = getpass.getpass('Confirmation: ')

        assert password == confirmation, 'password and confirmation must match'

    return password


def nth(generator, i):
    for current_iteration, data in enumerate(generator, 0):
        if current_iteration == i:
            return data


def first(generator):
    return nth(generator, 0)


def ignored(filename):
    patterns = [
        '.hg',
        '.git',
        '.env',
        '.DS_Store',
        '.localized'
    ]

    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True


def cleanup_path(path, keep_leading=False):
    path = path.replace('//', '/') \
        .rstrip('/')

    if not keep_leading:
        path = path.lstrip('/')

    return path


def copy_to_clipboard(value):
    pyperclip.copy(value)

    if pyperclip.paste() == value:
        return '*copied to clipboard*'

    return value
