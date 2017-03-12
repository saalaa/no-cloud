# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

from botocore.client import Config

from .s3 import RemoteStorage as S3RemoteStorage


class RemoteStorage(S3RemoteStorage):
    def check_s3_config(self):
        super(RemoteStorage, self).check_s3_config()

        assert 'endpoint' in self.config, '`endpoint` not found in configuration'

    def build_s3_args(self):
        args, kwargs = super(RemoteStorage, self).build_s3_args()

        if 'endpoint' in self.config:
            kwargs['endpoint_url'] = self.config['endpoint']

        if 'region' not in self.config:
            kwargs['region_name'] = 'us-east-1'

        kwargs['config'] = Config(signature_version='s3v4')

        return args, kwargs
