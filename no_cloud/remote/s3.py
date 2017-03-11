# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import os
import boto3

from ..cli import echo
from .base import BaseRemoteStorage


class RemoteStorage(BaseRemoteStorage):
    def __init__(self, config, root):
        super(RemoteStorage, self).__init__(config, root)

        self.check_s3_config()

    def check_s3_config(self):
        assert 'key' in self.config, '`key` not found in configuration'
        assert 'secret' in self.config, '`secret` not found in configuration'
        assert 'bucket' in self.config, '`bucket` not found in configuration'

    def build_s3_args(self):
        args = ('s3', )
        kwargs = {
            'aws_access_key_id': self.config['key'],
            'aws_secret_access_key': self.config['secret']
        }

        if 'region' in self.config:
            kwargs['region_name'] = self.config['region']

        return args, kwargs

    def __enter__(self):
        args, kwargs = self.build_s3_args()

        s3 = boto3.resource(*args, **kwargs)
        self.bucket = s3.Bucket(self.config['bucket'])

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

        self.bucket.upload_file(filename, remote_filename)

    def pull(self, path):
        remote_path = self.to_remote(path)

        for object_summary in self.bucket.objects.filter(Prefix=remote_path):
            local_filename = self.to_local(object_summary.key)

            echo(local_filename)

            dirname = os.path.dirname(local_filename)

            if not os.path.exists(dirname):
                os.makedirs(dirname)

            self.bucket.download_file(object_summary.key, local_filename)
