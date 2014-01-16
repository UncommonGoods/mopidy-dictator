from __future__ import unicode_literals

import re
from setuptools import setup, find_packages


def get_version(filename):
    content = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", content))
    return metadata['version']


setup(
    name='Mopidy-Dictator',
    version=get_version('mopidy_dictator/__init__.py'),
    url='https://github.com/UncommonGoods/mopidy-dictator',
    license='Apache License, Version 2.0',
    author='Nathan Harper',
    author_email='nharper@uncommongoods.com',
    description='Plugin for ruling your Mopidy server with an iron fist.',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 0.16a0',
        'Pykka >= 1.1',
        # 'pylast >= 0.5.7',
    ],
    # test_suite='nose.collector',
    # tests_require=[
    #     'nose',
    #     'mock >= 1.0',
    # ],
    entry_points={
        'mopidy.ext': [
            'dictator = mopidy_dictator:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
