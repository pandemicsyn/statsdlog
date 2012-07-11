# statsdlog #

Simple daemon that consumes a syslog udp stream and generates statsd events when certain log lines are encountered.

### Configuration ###

statsdlog sample config:

    [main]
    #debug = false
    #statsd_host = 127.0.0.1
    #statsd_port = 8125
    #statsd_sample_rate = 1.0
    #listen_addr = 127.0.0.1
    #listen_port = 8126
    #buffer_size = 8192
    #max_line_backlog = 512
    #report internals stats about statsdlog to statsd
    #report_internal_stats = false
    # if enabled report internal stats every 5 seconds
    #internal_stats_interval = 5
    # file that contains your log search patterns and statsd event names
    patterns_file = /etc/statsdlog/patterns.json

 - Copy etc/statsdlog/patterns.json to /etc/statsdlog/patterns.json
 - Edit patterns.json to include the regex patterns for log lines you want to fire events for.
 - Copy etc/statsdlog/statsdlog.conf-sample to /etc/statsdlog/statsdlog.conf
 - Edit the the conf file to point to your statsd host
 - Point syslog udp stream to 127.0.0.1:8126
 - ``python bin/statsdlog-server --conf=/etc/statsdlog/statsdlog.conf start``
 - Profit!

Its important to note that the first match wins. An event will only be fired for the first match.

The included patterns.json example includes a few patterns for errors commonly encountered when running [swift](http://github.com/openstack/swift)

### Installing ###

via setup.py:

 - ``git clone git://github.com/pandemicsyn/statsdlog.git``
 - ``cd statsdlog``
 - ``python setup.py install``

etc/statsdlog/statsdlog.init is available as a simple init script.

via pip (No sample configs or init script. Just the goods!):

 - ``pip install statsdlog``

### Building packages ###

Clone the version you want and build the package with [stdeb](https://github.com/astraw/stdeb "stdeb") (sudo apt-get install stdeb):

    git clone git@github.com:pandemicsyn/statsdlog.git statsdlog-0.0.5
    cd statsdlog-0.0.5
    git checkout 0.0.5
    python setup.py --command-packages=stdeb.command bdist_deb
    dpkg -i deb_dist/python-statsdlog_0.0.5-1_all.deb
