#!/usr/bin/env python
from setuptools import find_packages, setup


def readme():
    with open("README.md") as readme_file:
        return readme_file.read()


setup(
    name="samsungtvws",
    version="2.7.0",
    description="Samsung Smart TV WS API wrapper",
    long_description=readme(),
    long_description_content_type="text/markdown",
    author="Xchwarze",
    python_requires=">=3.0.0",
    url="https://github.com/xchwarze/samsung-tv-ws-api",
    package_data={"samsungtvws": ["py.typed"]},
    packages=find_packages(exclude=("tests",)),
    install_requires=["websocket-client>=0.57.0", "requests>=2.21.0"],
    extras_require={
        "async": ["aiohttp>=3.8.1", "websockets>=13"],
        "encrypted": ["cryptography>=35.0.0", "py3rijndael>=0.3.3"],
    },
    include_package_data=True,
    license="LGPL-3.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    ],
)
