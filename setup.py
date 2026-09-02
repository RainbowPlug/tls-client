#!/usr/bin/env python
from setuptools import setup, find_packages
from codecs import open
import glob
import sys
import os


# Only ship the unversioned loader binaries the runtime actually loads
# (tls_client/utils.py:get_dependency_filename), NOT the accumulated historical
# versioned/xgo binaries in dependencies/ - those bloated the wheel to ~470 MB,
# over PyPI's 100 MB per-file limit. This keeps the wheel ~60 MB.
_LOADER_FILES = [
    'tls-client-64.dll', 'tls-client-32.dll',
    'tls-client-amd64.so', 'tls-client-arm64.so', 'tls-client-x86.so',
    'tls-client-arm64.dylib', 'tls-client-x86.dylib',
    'version.txt',
]
data_files = [(
    'tls_client/dependencies',
    [os.path.join('tls_client/dependencies', f) for f in _LOADER_FILES
     if os.path.exists(os.path.join('tls_client/dependencies', f))],
)]

about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "tls_client", "__version__.py"), "r", "utf-8") as f:
    exec(f.read(), about)

with open("README.md", "r", "utf-8") as f:
    readme = f.read()

setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    description=about["__description__"],
    license = "MIT",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=False,
    package_data={
        'tls_client': ['dependencies/' + f for f in _LOADER_FILES],
    },
    # Both are imported at MODULE level, so without them the package installs
    # cleanly and then fails on `import tls_client`:
    #   response.py:7   from requests import HTTPError
    #   settings.py:1   from typing_extensions import Literal, TypeAlias
    # There was no install_requires at all, so a standalone
    # `pip install tls_client2` produced an unimportable package. It only ever
    # worked because every consumer happened to list requests and
    # typing_extensions separately in its own requirements file, which makes
    # this a landmine for the first environment that does not.
    # requirements.txt pins these exactly; kept as floors here so we do not
    # fight a consumer's own pin.
    install_requires=[
        'requests>=2.31',
        'typing_extensions>=4.12',
    ],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries",
    ],
    project_urls={
        "Source": "https://github.com/iamtorsten/tls-client",
    }
)