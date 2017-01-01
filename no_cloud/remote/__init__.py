# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

def get_remote(config, root, instantiate=True):
    assert 'driver' in config, 'invalid configuration'

    name = 'no_cloud.remote.' + config['driver']
    fromlist = [
        'RemoteStorage'
    ]

    module = __import__(name, fromlist=fromlist, level=0)

    if not instantiate:
        return module.RemoteStorage

    return module.RemoteStorage(config, root)
