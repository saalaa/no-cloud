# no-cloud

There is no cloud.


## Installation

    pip install no-cloud


## Usage

### Audit files for security issues

Files that are not encrypted (c) or have an incorrect mode set (m) are printed
to stdout. File modes are fixed by default.

    $ no-cloud audit ~/Documents
     m /home/benoit/Documents/.no-cloud.yml.crypt
    c  /home/benoit/Documents/diamond.db
       /home/benoit/Documents/letters/2016-12-20-santa.md.crypt
    ...

Options:

- `-d`, `--dry-run`: do not perform anything (ie.: not file mode fixing).


### Decrypt files using a password

Decrypt a Fernet encrypted files. Unless `--keep` is passed, the command will
remove the encrypted version of the file.

Encrypted files must have the `.crypt` extension.

    $ no-cloud decrypt ~/Documents/letters
    Decryption password: ***
    /home/benoit/Documents/letters/2016-12-20-santa.md.crypt

Options:

- `-d`, `--dry-run`: do not perform anything.
- `-k`, `--keep`: leave encrypted files behind.


### Encrypt files using a password

Encrypt files using Fernet encryption. Unless `--keep` is passed, the command
will remove the clear version of the file.

Encrypted files have the `.crypt` extension.

    $ no-cloud encrypt ~/Documents/letters
    Encryption password: ***
    Confirmation: ***
    /home/benoit/Documents/letters/2016-12-20-santa.md

Options:

- `-d`, `--dry-run`: do not perform anything.
- `-k`, `--keep`: leave clear files behind.


### Reproducibly generate passwords

Passwords are built using the SHA512 hashing function and a configurable
digest function (depending on what characters should be supported).

To compute passwords, it uses the service name, the user name and a master
password. The number of iterations of the algorithm can be tweaked which is
especially useful for password rotation (you should keep it above 100000 which
is the default).

The hashing function is ran twice, first on the user name using the master
password as salt and then on the service name using the initial result as salt.

This command will print sensitive information to standard output so you *must*
make sure this does not represent a security issue.

- Set your terminal output history (or scrollback) to a sensible value with no
  saving or restoration.
- Activate history skipping in your shell and put a whitespace before the
  command (or whatever it supports).

Passwords are copied to the clipboard unless `--no-clipboard` is passed.

    $ no-cloud password --service example.com --username rob@example.com
    Master password: ***
    Confirmation: ***
    service: example.com
    username: rob@example.com
    password: *copied to clipboard*

This command also supports reading credentials from a YAML file through the
`--filename` option. It can be transparently encrypted (highly recommended).
The master password will *always* be prompted for.

When reading credentials from a YAML file, the `--version` can be used to
determine what YAML document should be used (by default, the first version found
is used).

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

    $ no-cloud encrypt ~/Documents/passwords/example.yml
    Encryption password: ***
    Confirmation: ***
    /home/benoit/Documents/passwords/example.yml

And passwords can be generated:

    $ no-cloud password -f ~/Documents/passwords/example.yml.crypt
    Decryption password: ***
    Master password: ***
    Confirmation: ***
    service: example.com
    username: rob@example.com
    password: *copied to clipboard*
    comment: >
      Updated on 2016-12-20

Options:

- `-s`, `--service`: service to generate a password for.
- `-u`, `--username`: user name to generate a password for.
- `-i`, `--iterations`: number of iterations for the SHA512 algorithm (defaults
  to 100000).
- `-c`, `--characters`: characters classes to use for the digest; `l` for
  lowercase, `u` for uppercase, `d` for digits and `p` for punctuation (defaults
  to `ludp`).
- `-l`, `--length`: length of the digest (defaults to 32).
- `-f`, `--filename`: YAML file to read the above information from.
- `-v`, `--version`: YAML document starting at zero (defaults to 0).
- `-n`, `--no-clipboard`: disable clipboard copy, password is printed to stdout.


### Pull files from remote storage

This command will pull files from remote storage, overriding any previously
existing local file.

    $ no-cloud pull ~/Documents/passwords

Remote configuration is found recursively starting from the path provided.
See `remote` for more information.


### Push files to remote storage

This command will push files to remote storage, overriding any previously
existing remote file.

    $ no-cloud push ~/Documents/passwords

Remote configuration is found recursively starting from the path provided.
See `remote` for more information.


### Remote configuration for `pull` and `push` commands

Both `pull` and `push` commands rely on `.no-cloud.yml` (which can be
transparently encrypted for figuring out remote information. Configuration
files are looked for recursively starting from the path provided to said
commands.

Sample configuration for S3:

    driver: s3
    bucket: bucket-xyz
    region: eu-west-1
    key: PRIVATE_KEY
    secret: SECRET

Sample configuration for SFTP (not yet implemented):

    driver: sftp
    host: example.com
    user: root
    private_key: >
      -----BEGIN RSA PRIVATE KEY-----
      ...
      -----END RSA PRIVATE KEY-----

### Rename files using a substition pattern

Substitution patterns follow the form `s/pattern/replacement/`. Unless `--force`
is passed, the command will not overwrite existing files.

    $ no-cloud rename 's/monica/hillary/' *.png

The special `$i` replacement variable holds the current iteration starting at
one and left-padded with zeros according to the number of target files.

    $ no-cloud rename 's/^/$i-/' *.png

Options:

- `-d`, `--dry-run`: do not perform anything.
- `-f`, `--force`: force renaming, possibly overwriting existing files.

### Render a Markdown file as a PDF

Sample usage:

    $ no-cloud render -p ~/Documents/letters/2016-12-20-santa.md
    /home/benoit/Documents/letters/2016-12-20-santa.pdf

Markdown rendering supports custom classes through annotations (eg.
`{: .right}`); here are some classes defined in the default CSS:

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

Options:

- `-p`, `--preview`: automatically preview document.
- `-t`, `--timestamp`: timestamp PDF file.
- `-s`, `--stylesheet`: CSS stylesheet.
