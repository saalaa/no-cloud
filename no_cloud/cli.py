# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import os
import re
import sys
import click
import string

from .remote import get_remote
from .utils import get_password, copy_to_clipboard
from .crypto import fernet_encrypt, fernet_decrypt, sha512_hash, digest
from .fs import (
    find_in_path, load_configuration, is_encrypted, list_files, test_mode,
    fix_mode
)


def die(message):
    click.echo('Error: %s' % message)
    sys.exit(1)


def echo(message=''):
    if type(message) in (dict, list, tuple):
        message = __import__('json').dumps(message, indent=2)

    click.echo(message)


def main():
    try:
        cli(obj={})
    except AssertionError as e:
        die(e)


@click.group()
def cli():
    pass


@cli.command()
def remote():
    '''Configuring push/pull commands.

    Sample configuration for S3:

        \b
        driver: s3
        bucket: bucket-xyz
        region: eu-west-1
        key: PRIVATE_KEY
        secret: SECRET

    Sample configuration for SFTP:

        \b
        driver: sftp
        host: example.com
        user: root
        private_key: >
          -----BEGIN RSA PRIVATE KEY-----
          ...
          -----END RSA PRIVATE KEY-----
    '''
    echo(remote.__doc__)


@cli.command()
@click.argument('paths', nargs=-1)
def push(paths):
    '''Push files to remote storage.

    This command will push files to remote storage, overriding any previously
    existing file.

        push .
    '''
    for path in paths:
        root, filename = find_in_path(path, '.no-cloud.yml.crypt',
                '.no-cloud.yml')

        assert root and filename, 'no configuration found'

        config = load_configuration(root + '/' + filename)

        with get_remote(config, root) as remote:
            for filename in list_files(path):
                remote.push(filename)


@cli.command()
@click.argument('paths', nargs=-1)
def pull(paths):
    '''Pull files from remote storage.

    This command will pull files from remote storage, overriding any previously
    existing file.

        pull .
    '''
    for path in paths:
        root, filename = find_in_path(path, '.no-cloud.yml.crypt',
                '.no-cloud.yml')

        assert root and filename, 'no configuration found'

        config = load_configuration(root + '/' + filename)

        with get_remote(config, root) as remote:
            remote.pull(path)


@cli.command()
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything.')
@click.option('-k', '--keep', is_flag=True, help='')
@click.argument('paths', nargs=-1)
def encrypt(dry_run, keep, paths):
    '''Encrypt files using a passphrase.

        encrypt ~/Documents/invoices
    '''
    password = None if dry_run else get_password('Encryption password',
            confirm=True)

    for filename in list_files(paths):
        if is_encrypted(filename):
            continue

        echo(filename)

        if dry_run:
            continue

        with open(filename, 'rb') as file:
            data = file.read()

        data = fernet_encrypt(data, password)

        with open(filename + '.crypt', 'wb') as file:
            file.write(data)

        if not keep:
            os.remove(filename)


@cli.command()
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything.')
@click.option('-k', '--keep', is_flag=True, help='')
@click.argument('paths', nargs=-1)
def decrypt(dry_run, keep, paths):
    '''Decrypt files using a passphrase.

        decrypt ~/Documents/invoices
    '''
    password = None if dry_run else get_password('Decryption Password')

    for filename in list_files(paths):
        if not is_encrypted(filename):
            continue

        echo(filename)

        if dry_run:
            continue

        with open(filename, 'rb') as file:
            data = file.read()

        data = fernet_decrypt(data, password)

        filename, ext = os.path.splitext(filename)
        with open(filename, 'wb') as file:
            file.write(data)

        if not keep:
            os.remove(filename + ext)


@cli.command()
@click.option('-s', '--service', help='', default='')
@click.option('-u', '--username', help='', default='')
@click.option('-i', '--iterations', help='', default=100000)
@click.option('-c', '--characters', help='', default='ludp')
@click.option('-l', '--length', help='', default=32)
@click.option('-f', '--filename', help='', default=None)
@click.option('-v', '--version', help='', default=0)
def password(service, username, iterations, characters, length, filename,
        version):
    '''Reproducibly generate passwords.

    Note that `-f` supports encrypted files.

    Sample YAML file with several versions:

        service: example.com
        username: root@example.com
        iterations: 110000
        comment: >
          Updated on 2016-12-18
        ---
        service: example.com
        username: root@example.com
        comment: >
          Updated on 2016-12-18
    '''
    config = {
        'service': service,
        'username': username,
        'iterations': iterations,
        'characters': characters,
        'length': length
    }

    if filename:
        data = load_configuration(filename, version)

        config.update(data)

    assert config['service'], 'missing service'
    assert config['username'], 'missing username'
    assert config['length'] > 0, 'invalid length'

    characters = ''
    if 'l' in config['characters']:
        characters += string.lowercase * 3
    if 'u' in config['characters']:
        characters += string.uppercase * 3
    if 'd' in config['characters']:
        characters += string.digits * 3
    if 'p' in config['characters']:
        characters += string.punctuation * 2

    assert len(characters), 'invalid characters'

    password = get_password('Master password', confirm=True)

    hashed = sha512_hash(config['username'], password, config['iterations'])
    hashed = sha512_hash(config['service'], hashed, config['iterations'])

    hashed = digest(hashed, characters, config['length'])

    hashed = copy_to_clipboard(hashed)

    echo('service: %s' % data['service'])
    echo('username: %s' % data['username'])
    echo('password: %s' % hashed)
    echo('comment: >')
    echo('  %s' % data.get('comment', '').strip())


@cli.command()
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything.')
@click.option('-f', '--force', is_flag=True, help='Force renaming, possibly '
    'overwriting existing files.')
@click.argument('pattern', nargs=1)
@click.argument('paths', nargs=-1)
def rename(dry_run, force, pattern, paths):
    '''Rename files using a substition pattern.

    Patterns follow the form `s/pattern/replacement/`. Unless `--force` is
    passed, the command will not overwrite existing files.

    To prefix files with a serial number:

        rename 's/^/road-trip-$i-/' *.png
    '''
    assert pattern.startswith('s/'), 'invalid pattern'
    assert pattern.endswith('/'), 'invalid pattern'

    filenames = list_files(paths)
    filenames = tuple(filenames)

    length = len(filenames)
    length = str(length)
    length = len(length)

    fmt = '%0' + str(length) + 'd'

    files = [{'src': file, 'dst': None} for file in filenames]

    pattern, replacement = pattern[2:-1].split('/', 1)
    pattern = re.compile(pattern)

    i = 1
    for file in files:
        repl = replacement[:].replace('$i', fmt % i)
        file['dst'] = pattern.sub(repl, file['src'])

        echo(file['dst'])

        if not dry_run:
            if not force:
                assert not os.path.isfile(file['dst']), \
                        'destination exists `%s`' % file['dst']

            os.rename(file['src'], file['dst'])

        i += 1


@cli.command()
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything.')
@click.argument('paths', nargs=-1)
def audit(dry_run, paths):
    '''Audit files for security issues.

    Files that are not encrypted (c) or have an incorrect mode set (m) are
    printed to stdout. Mode are fixed by default.

        audit ~/Documents
    '''
    for filename in list_files(paths):
        clear = not is_encrypted(filename)
        mode = not test_mode(filename)

        status = '' \
            + ('c' if clear else ' ') \
            + ('m' if mode else ' ')

        echo('%s %s' % (status, filename))

        if mode and not dry_run:
            fix_mode(filename)
