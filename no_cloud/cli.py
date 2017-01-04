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
    '''Remote configuration for `pull` and `push` commands.

    Both `pull` and `push` commands rely on `.no-cloud.yml` (which can be
    transparently encrypted for figuring out remote information. Configuration
    files are looked for recursively starting from the path provided to said
    commands.

    Sample configuration for S3:

        \b
        driver: s3
        bucket: bucket-xyz
        region: eu-west-1
        key: PRIVATE_KEY
        secret: SECRET

    Sample configuration for SFTP (not yet implemented):

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
    existing remote file.

        $ no-cloud push ~/Documents/passwords

    Remote configuration is found recursively starting from the path provided.
    See `remote` for more information.
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
    existing local file.

        $ no-cloud pull ~/Documents/passwords

    Remote configuration is found recursively starting from the path provided.
    See `remote` for more information.
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
@click.option('-k', '--keep', is_flag=True, help='Leave clear files behind.')
@click.argument('paths', nargs=-1)
def encrypt(dry_run, keep, paths):
    '''Encrypt files using a passphrase.

    Encrypt files using Fernet encryption. Unless `--keep` is passed, the
    command will remove the clear version of the file.

    Encrypted files have the `.crypt` extension.

        \b
        $ no-cloud encrypt ~/Documents/letters
        Encryption password: ***
        Confirmation: ***
        /home/benoit/Documents/letters/2016-12-20-santa.md
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
@click.option('-k', '--keep', is_flag=True, help='Leave encrypted files '
        'behind.')
@click.argument('paths', nargs=-1)
def decrypt(dry_run, keep, paths):
    '''Decrypt files using a password.

    Decrypt a Fernet encrypted files. Unless `--keep` is passed, the command
    will remove the encrypted version of the file.

    Encrypted files must have the `.crypt` extension.

        \b
        $ no-cloud decrypt ~/Documents/letters
        Decryption password: ***
        /home/benoit/Documents/letters/2016-12-20-santa.md.crypt
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
@click.option('-s', '--service', help='', default='Service to generate a '
        'password for.')
@click.option('-u', '--username', help='', default='User name to generate a '
        'password for.')
@click.option('-i', '--iterations', help='Number of iterations for the SHA512 '
        'algorithm (defaults to 100000).', default=100000)
@click.option('-c', '--characters', help='Characters classes to use for the '
        'digest; `l` for lowercase, `u` for uppercase, `d` for digits and `p` '
        'for punctuation (defaults to `ludp`).', default='ludp')
@click.option('-l', '--length', help='Length of the digest (defaults to 32).',
        default=32)
@click.option('-f', '--filename', help='YAML file to read the above '
        'information from.', default=None)
@click.option('-v', '--version', help='YAML document starting at zero '
        '(defaults to 0).', default=0)
@click.option('-n', '--no-clipboard', is_flag=True, help='Disable clipboard '
        'copy, password is printed to stdout.')
def password(service, username, iterations, characters, length, filename,
        version, no_clipboard):
    '''Reproducibly generate passwords.

    Passwords are built using the SHA512 hashing function and a configurable
    digest function (depending on what characters should be supported).

    To compute passwords, it uses the service name, the user name and a master
    password. The number of iterations of the algorithm can be tweaked which is
    especially useful for password rotation (you should keep it above 100000
    which is the default).

    The hashing function is ran twice, first on the user name using the master
    password as salt and then on the service name using the initial result as
    salt.

    This command will print sensitive information to standard output so you
    *must* make sure this does not represent a security issue.

    \b
    - Set your terminal output history (or scrollback) to a sensible value with
      no saving or restoration.
    - Activate history skipping in your shell and put a whitespace before the
      command (or whatever it supports).

    Passwords are copied to the clipboard unless `--no-clipboard` is passed.

        \b
        $ no-cloud password --service example.com --username rob@example.com
        Master password: ***
        Confirmation: ***
        service: example.com
        username: rob@example.com
        password: *copied to clipboard*

    This command also supports reading credentials from a YAML file through the
    `--filename` option. It can be transparently encrypted (highly
    recommended). The master password will *always* be prompted for.

    When reading credentials from a YAML file, the `--version` can be used to
    determine what YAML document should be used (by default, the first version
    found is used).

        \b
        $ cat ~/Documents/passwords/example.yml
        service: example.com
        username: root@example.com
        iterations: 110000
        comment: >
          Updated on 2016-12-20
        ---
        service: example.com
        username: root@example.com
        comment: >
          Updated on 2016-11-20

    We can now encrypt this file:

        \b
        $ no-cloud encrypt ~/Documents/passwords/example.yml
        Encryption password: ***
        Confirmation: ***
        /home/benoit/Documents/passwords/example.yml

    And passwords can be generated:

        \b
        $ no-cloud password -f ~/Documents/passwords/example.yml.crypt
        Decryption password: ***
        Master password: ***
        Confirmation: ***
        service: example.com
        username: rob@example.com
        password: *copied to clipboard*
        comment: >
          Updated on 2016-12-20
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

    if not no_clipboard:
        hashed = copy_to_clipboard(hashed)

    echo('service: %s' % config['service'])
    echo('username: %s' % config['username'])
    echo('password: %s' % hashed)

    if 'comment' in config:
        echo('comment: >')
        echo('  %s' % config['comment'].strip())


@cli.command()
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything.')
@click.option('-f', '--force', is_flag=True, help='Force renaming, possibly '
    'overwriting existing files.')
@click.argument('pattern', nargs=1)
@click.argument('paths', nargs=-1)
def rename(dry_run, force, pattern, paths):
    '''Rename files using a substition pattern.

    Substitution patterns follow the form `s/pattern/replacement/`. Unless
    `--force` is passed, the command will not overwrite existing files.

        $ no-cloud rename 's/monica/hillary/' *.png

    The special `$i` replacement variable holds the current iteration starting
    at one and left-padded with zeros according to the number of target files.

        $ no-cloud rename 's/^/$i-/' *.png
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
@click.option('-d', '--dry-run', is_flag=True, help='Do not perform anything '
        '(ie.: not file mode fixing).')
@click.argument('paths', nargs=-1)
def audit(dry_run, paths):
    '''Audit files for security issues.

    Files that are not encrypted (c) or have an incorrect mode set (m) are
    printed to stdout. File modes are fixed by default.

        \b
        $ no-cloud audit ~/Documents
         m /home/benoit/Documents/.no-cloud.yml.crypt
        c  /home/benoit/Documents/diamond.db
           /home/benoit/Documents/letters/2016-12-20-santa.md.crypt
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
