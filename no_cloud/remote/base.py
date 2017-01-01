# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

class BaseRemoteStorage(object):
    def __init__(self, config, root):
        self.config = config
        self.root = root

    def __enter__(self):
        raise NotImplementedError

    def __exit__(self, *args):
        pass

    def push(self, filename):
        raise NotImplementedError

    def pull(self, path):
        raise NotImplementedError
