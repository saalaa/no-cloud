# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

from boto.s3.connection import S3Connection

from ..cli import echo
from .base import BaseRemoteStorage


class RemoteStorage(BaseRemoteStorage):
    def __init__(self, config, root):
        super(RemoteStorage, self).__init__(config, root)

        assert 'key' in config, 'invalid configuration'
        assert 'secret' in config, 'invalid configuration'
        assert 'bucket' in config, 'invalid configuration'

    def __enter__(self):
        self.connection = S3Connection(self.config['key'],
                self.config['secret'])
        self.bucket = self.connection.create_bucket(self.config['bucket'])

        return self

    def __exit__(self, *args):
        pass

    def to_remote(self, path):
        if not path.startswith(self.root):
            return path

        length = len(self.root)

        return path[length:].lstrip('/')

    def to_local(self, path):
        return self.root + '/' + path

    def push(self, filename):
        remote_filename = self.to_remote(filename)

        echo(filename)

        key = self.bucket.new_key(remote_filename)
        key.set_contents_from_filename(filename)

    def pull(self, path):
        remote_path = self.to_remote(path)

        for key in self.bucket.list(remote_path):
            local_filename = self.to_local(key.name)

            echo(local_filename)

            key.get_contents_to_filename(local_filename)
