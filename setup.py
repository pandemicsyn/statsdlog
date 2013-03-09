from setuptools import setup, find_packages
from statsdlog import __version__ as version

install_requires = []
try:
    import eventlet
except ImportError:
    install_requires.append("eventlet")

name = "statsdlog"

data_files = [('share/doc/statsdlog',
               ['README.md',
                'etc/statsdlog/patterns.json',
                'etc/statsdlog/patterns.json-authlog',
                'etc/statsdlog/patterns.json-dpkglog',
                'etc/statsdlog/patterns.json-nginx',
                'etc/statsdlog/patterns.json-openstackswift',
                'etc/statsdlog/statsdlog.conf-sample',
                'etc/statsdlog/statsdlog.init-sample'])]

setup(
    name = name,
    version = version,
    author = "Florian Hines",
    author_email = "syn@ronin.io",
    description = "generate statsd events by monitoring a syslog udp stream",
    license = "Apache License, (2.0)",
    keywords = "statsd syslog graphite",
    url = "http://github.com/pandemicsyn/statsdlog",
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Environment :: No Input/Output (Daemon)',
        ],
    install_requires=install_requires,
    scripts=['bin/statsdlog-server'],
    data_files = data_files,
    )
