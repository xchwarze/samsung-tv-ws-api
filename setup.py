#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup, Command


def readme():
    with open('README.md') as readme_file:
        return readme_file.read()


setup(
    name='samsungtvws',
    version='1.1.6',
    description='Samsung Smart TV WS API wrapper',
    long_description=readme(),
    long_description_content_type='text/markdown',
    author='Xchwarze',
    python_requires='>=3.0.0',
    url='https://github.com/xchwarze/samsung-tv-ws-api',
    packages=find_packages(exclude=('tests',)),
    install_requires=['websocket-client'],
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License'
    ]
)
