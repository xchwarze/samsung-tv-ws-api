#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup


def readme():
    with open('README.md') as readme_file:
        return readme_file.read()


setup(
    name='samsungtvws',
    version='1.5.1',
    description='Samsung Smart TV WS API wrapper',
    long_description=readme(),
    long_description_content_type='text/markdown',
    author='Xchwarze',
    python_requires='>=3.0.0',
    url='https://github.com/xchwarze/samsung-tv-ws-api',
    packages=find_packages(exclude=('tests',)),
    install_requires=[
        'websocket-client>=0.56.0',
        'requests>=2.21.0'
    ],
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License'
    ]
)
