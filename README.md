# statsdlog #

Simple daemon that consumes a syslog udp stream and generates statsd events when certain log lines are encountered.

### Configuration ###

statsdlog sample config:

    [main]
    debug = true
    #statsd_host = 127.0.0.1
    #statsd_port = 8125
    #statsd_sample_rate = 1.0
    #listen_addr = 127.0.0.1
    #listen_port = 8126
    #mgmt_enabled = true
    #mgmt_addr = 127.0.0.1
    #mgmt_port = 8127
    #buffer_size = 8192
    #max_line_backlog = 512
    # file that contains your log search patterns and statsd event names
    patterns_file = /etc/statsdlog/patterns.json

 - Edit patterns.json to include the regex patterns for log lines you want to fire events for.
 - Point the conf file to your statsd host
 - Point syslog udp stream to 127.0.0.1:8126
 - Profit

Its important to note that the first match wins. An event will only be fired for the first match.

The included patterns.json example includes a few patterns for errors commonly encountered when running [swift](http://github.com/openstack/swift)

### Building packages ###

Clone the version you want and build the package with [stdeb](https://github.com/astraw/stdeb "stdeb") (sudo apt-get install stdeb):
    
    git clone git@github.com:pandemicsyn/statsdlog.git statsdlog-0.0.3
    cd statsdlog-0.0.3
    git checkout 0.0.3
    python setup.py --command-packages=stdeb.command bdist_deb
    dpkg -i deb_dist/python-statsdlog_0.0.3-1_all.deb
