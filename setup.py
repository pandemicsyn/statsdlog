from setuptools import setup, find_packages

from informant import __version__ as version

name = "statsdlog"

setup(
    name = name,
    version = version,
    author = "Florian Hines",
    author_email = "syn@ronin.io",
    description = "statsdlog",
    license = "Apache License, (2.0)",
    keywords = "statsd syslog",
    url = "http://github.com/pandemicsyn/statsdlog",
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Environment :: No Input/Output (Daemon)',
        ],
    install_requires=[],
    scripts=['bin/statsdlog-server']
    )
