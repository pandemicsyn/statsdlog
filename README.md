 - Edit patterns.json to include the regex patterns for log lines you want to fire events for.
 - Point the conf file to your statsd host
 - Point syslog udp stream to 127.0.0.1:8126
 - Profit

The included patterns.json example includes a few patterns for [swift](http://github.com/openstack/swift)
