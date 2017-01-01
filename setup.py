# Copyright (C) 2016 Benoit Myard <myardbenoit@gmail.com>
# Released under the terms of the BSD license.

import re

from setuptools import setup

VERSION_RE = re.compile(r"__version__ = '(.*)'")


def version(filename):
    with open(filename) as file:
        source = file.read()

    return VERSION_RE.search(source).group(1)


def requirements(filename):
    with open(filename) as file:
        source = file.read()

    return source.split()


version = version('no_cloud/__init__.py')
requirements = requirements('requirements.txt')


setup(
    name='no-cloud',
    version=version,
    url='http://github.com/saalaa/no-cloud',
    license='BSD',
    author='Benoit Myard',
    author_email='myardbenoit@gmail.com',
    description='There is no cloud',
    install_requires=requirements,
    zip_safe=False,
    platforms='any',
    packages=[
        'no_cloud',
        'no_cloud.remote'
    ],
    entry_points={
        'console_scripts': [
            'no-cloud = no_cloud.cli:main'
        ]
    },
    classifiers=[
        'Topic :: Utilities',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
    ]
)
