# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import os
import re
import sys
import click
import string
import datetime
import subprocess


from . import __version__
from .remote import get_remote
from .crypto import fernet_encrypt, fernet_decrypt, sha512_hash, digest
from .formatter import make_html
from .utils import get_password, copy_to_clipboard
from .fs import (
    find_in_path, load_configuration, is_encrypted, list_files, test_mode,
    fix_mode, asset_path
)

DEFAULT_CSS = 'stylesheet.css'
DATE_YMD = '%Y-%m-%d'


def die(message):
    click.echo('Error: %s' % message)
    sys.exit(1)


def echo(message=''):
    if type(message) in (dict, list, tuple):
        message = __import__('json').dumps(message, indent=2)

    click.echo(message)


def main():
    try:
        __import__('weasyprint')
    except ValueError as e:
        if 'unknown locale' not in str(e):
            raise e

        # Fix locale on Mac OS.
        os.environ['LC_CTYPE'] = 'en_US'

    try:
        cli(obj={})
    except AssertionError as e:
        die(e)


@click.group(invoke_without_command=True)
@click.option('-v', '--version', is_flag=True, help='Print program version.')
def cli(version):
    if version:
        echo(__version__)


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

    Sample configuration for Minio (also uses S3):

        \b
        driver: minio
        endpoint: https://minio.example.com
        bucket: documents
        key: PRIVATE_KEY
        secret: SECRET
    '''
    doc = remote.__doc__

    doc = re.sub(r'^    ', '', doc, flags=re.M)
    doc = re.sub('    \b\n', '', doc, flags=re.M)

    echo(doc)


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

    def done(password):
        if not no_clipboard:
            password = copy_to_clipboard(password)

        echo('service: %s' % config['service'])
        echo('username: %s' % config['username'])
        echo('password: %s' % password)

        if 'comment' in config:
            echo('comment: >')
            echo('  %s' % config['comment'].strip())

    if filename:
        data = load_configuration(filename, version)

        config.update(data)

    assert config['service'], 'missing service'
    assert config['username'], 'missing username'
    assert config['length'] > 0, 'invalid length'

    if 'password' in config:
        return done(config['password'])

    characters = ''
    if 'l' in config['characters']:
        characters += string.ascii_lowercase * 3
    if 'u' in config['characters']:
        characters += string.ascii_uppercase * 3
    if 'd' in config['characters']:
        characters += string.digits * 3
    if 'p' in config['characters']:
        characters += string.punctuation * 2

    assert len(characters), 'invalid characters'

    password = get_password('Master password', confirm=True)

    hashed = sha512_hash(config['username'], password, config['iterations'])
    hashed = sha512_hash(config['service'], hashed, config['iterations'])

    hashed = digest(hashed, characters, config['length'])

    done(hashed)


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

    files = []
    for filename in filenames:
        files.append({
            'path': os.path.dirname(filename),
            'src': os.path.basename(filename),
            'dst': None
        })

    pattern, replacement = pattern[2:-1].split('/', 1)
    pattern = re.compile(pattern)

    i = 1
    for file in files:
        repl = replacement[:].replace('$i', fmt % i)
        file['dst'] = pattern.sub(repl, file['src'])

        file['src'] = file['path'] + '/' + file['src']
        file['dst'] = file['path'] + '/' + file['dst']

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


@cli.command()
@click.option('-p', '--preview', is_flag=True, help='Automatically preview '
        'document.')
@click.option('-t', '--timestamp', is_flag=True, help='Timestamp PDF file.')
@click.option('-s', '--stylesheet', help='CSS stylesheet.', default='default')
@click.argument('paths', nargs=-1)
def render(preview, timestamp, stylesheet, paths):
    '''Render a Markdown file as a PDF.

    Sample usage:

        \b
        $ no-cloud render -p ~/Documents/letters/2016-12-20-santa.md
        /home/benoit/Documents/letters/2016-12-20-santa.pdf

    Markdown rendering supports custom classes through annotations (eg.
    `{right}`); here are some classes defined in the default CSS:

    - `right`: align a block of text on the right-half of the page
    - `letter`: add 3em worth of indentation for the first line in
      paragraphs
    - `t-2` to `t-10`: add 2 to 10 em worth of top margin
    - `b-2` to `b-10`: add 2 to 10 em worth of bottom margin
    - `l-pad-1` to `l-pad-3`: add 1 to 3 em worth of left padding
    - `signature`: limit an image's width to 10em
    - `pull-right`: make an element float to the right
    - `break`: insert a page break before an element
    - `centered`: centered text
    - `light`: lighter gray text
    - `small`: smaller texter (0.9em)

    It also contains rules for links, code, citations, tables and horizontal
    rules.

    Please note that this feature may not work on Python2/Mac OS.
    '''
    from weasyprint import HTML, CSS

    for filename in list_files(paths):
        assert filename.endswith('.md'), ''

        with open(filename) as file:
            data = file.read()

        html = make_html(data)

        filename, ext = os.path.splitext(filename)

        if timestamp:
            now = datetime.datetime.now()

            dirname = os.path.dirname(filename)
            filename = os.path.basename(filename)

            filename = dirname + '/' + now.strftime(DATE_YMD) + '-' + filename

        filename = filename + '.pdf'

        if stylesheet == 'default':
            stylesheet = asset_path('stylesheet.css')

        echo(filename)

        HTML(string=html) \
            .write_pdf(filename, stylesheets=[
                CSS(stylesheet)
            ])

        if preview:
            subprocess.call(['open', filename])
