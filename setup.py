#!/usr/bin/env python3
#
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()

with open("bowler/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]

with open("requirements.txt") as f:
    requires = f.read().strip().splitlines()

setup(
    long_description=readme,
    version=version,
    packages=["bowler", "bowler.tests"],
    install_requires=requires,
    entry_points={"console_scripts": ["bowler = bowler.main:main"]},
)
