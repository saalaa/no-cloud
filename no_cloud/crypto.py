# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

from base64 import urlsafe_b64encode
from hashlib import md5, pbkdf2_hmac
from cryptography.fernet import Fernet, InvalidToken


def fernet_encrypt(message, password):
    password = md5(password).hexdigest()
    password = urlsafe_b64encode(password)

    return Fernet(password) \
            .encrypt(message)


def fernet_decrypt(message, password):
    password = md5(password).hexdigest()
    password = urlsafe_b64encode(password)

    try:
        return Fernet(password) \
                .decrypt(message)
    except InvalidToken:
        raise AssertionError('invalid decryption password')


def sha512_hash(message, salt, iterations=100000):
    return pbkdf2_hmac('sha512', message, salt, iterations)


def digest(hashed, characters, length=16):
    hashed = [ord(b) for b in hashed]

    digest = ''
    characters_length = len(characters)
    for c in hashed[-length:]:
        if c >= characters_length:
            c = c % characters_length

        digest += characters[c]

    return digest
