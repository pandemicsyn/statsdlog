import eventlet
from eventlet.green import socket
from eventlet.queue import Queue
from eventlet import wsgi
from daemonutils import Daemon, readconf
from random import random
try:
    import simplejson as json
except ImportError:
    import json
#via swift.common.utils
# logging doesn't import patched as cleanly as one would like
from logging.handlers import SysLogHandler
import logging
logging.thread = eventlet.green.thread
logging.threading = eventlet.green.threading
logging._lock = logging.threading.RLock()
import optparse
import sys
import re


class StatsdLog(object):

    def __init__(self, conf):
        TRUE_VALUES = set(('true', '1', 'yes', 'on', 't', 'y'))
        self.conf = conf
        self.logger = logging.getLogger('StatsdLog')
        self.logger.setLevel(logging.INFO)
        self.syslog = SysLogHandler(address='/dev/log')
        self.formatter = logging.Formatter('%(name)s: %(message)s')
        self.syslog.setFormatter(self.formatter)
        self.logger.addHandler(self.syslog)
        
        if conf.get('debug', False) in TRUE_VALUES:
            self.debug = True
        else:
            self.debug = False
        
        self.statsd_host = conf.get('statsd_host', '127.0.0.1')
        self.statsd_port = int(conf.get('statsd_port', '8125'))
        self.listen_addr = conf.get('listen_addr', '127.0.0.1')
        self.listen_port = int(conf.get('listen_port', 8126))
        
        if conf.get('mgmt_enabled', False) in TRUE_VALUES:
            self.mgmt = True
        else:
            self.mgmt = False
        
        self.mgmt_addr = conf.get('mgmt_addr', '127.0.0.1')
        self.mgmt_port = int(conf.get('mgmt_port', 8127))
        self.buff = int(conf.get('buffer_size', 8192))
        self.max_q_size = int(conf.get('max_line_backlog', 512))
        self.statsd_sample_rate = float(conf.get('statsd_sample_rate', '.5'))
        self.counter = 0
        self.skip_counter = 0
        self.hits = 0
        self.q = Queue(maxsize=self.max_q_size)
        # key: regex
        self.patterns_file = conf.get('patterns_file', 'patterns.json')
        
        try:
            with open(self.patterns_file) as f:
                self.patterns = json.loads(f.read())
        except Exception as e:
            self.logger.critical(e)
            print e
            sys.exit(1)
        
        self.statsd_addr = (self.statsd_host, self.statsd_port)
        self.comp_patterns = {}
        for item in self.patterns:
            self.comp_patterns[item] = re.compile(self.patterns[item])

    def check_line(self, line):
        for entry in self.comp_patterns:
            if self.comp_patterns[entry].match(line):
                return entry
        return None

    def stats_print(self):
        lastcount = 0
        lasthit = 0
        while True:
            eventlet.sleep(60)
            lps = (self.counter - lastcount) / 10
            hps = (self.hits - lasthit) / 10
            lastcount = self.counter
            lasthit = self.hits
            self.logger.info('per second: %d lines - hits %d' % (lps, hps))
            self.logger.info('totals: %d hits - %d lines' % \
                (self.hits, self.counter))
            if self.skip_counter is not 0:
                self.logger.info('Had to skip %d log lines so far' % \
                    self.skip_counter)

    def send_event(self, payload):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.sendto(payload, self.statsd_addr)
        except Exception:
            #udp sendto failed (socket already in use?), but thats ok
            self.logger.error("Error trying to send statsd event")

    def statsd_counter_increment(self, stats, delta=1):
        """
        Increment multiple statsd stats counters
        """
        if self.statsd_sample_rate < 1:
            if random() <= self.statsd_sample_rate:
                for item in stats:
                    payload = "%s:%s|c|@%s" % (item, delta,
                        self.statsd_sample_rate)
                    self.send_event(payload)
        else:
            for item in stats:
                payload = "%s:%s|c" % (item, delta)
                self.send_event(payload)

    def mgmt_app(self, env, start_response):
        if env['PATH_INFO'] == '/stats':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body = 'totals: %d hits - %d lines\r\n' % (self.hits, self.counter)
            return [body]
        else:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return ['Not Found\r\n']

    def run_mgmt_server(self):
        wsgi.server(eventlet.listen((self.mgmt_addr, self.mgmt_port)),
            self.mgmt_app)

    def worker(self):
        while True:
            msg = self.q.get()
            matched = self.check_line(msg)
            if matched:
                self.statsd_counter_increment([matched])
                self.hits += 1
            else:
                pass

    def listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bind_addr = (self.listen_addr, self.listen_port)
        sock.bind(bind_addr)
        self.logger.info("listening on %s:%d" % bind_addr)
        while 1:
            data, addr = sock.recvfrom(self.buff)
            if not data:
                break
            else:
                if self.q.qsize() < self.max_q_size:
                    self.q.put(data)
                    self.counter += 1
                else:
                    if self.debug:
                        self.logger.notice("max log lines in queue, skipping")
                    self.skip_counter += 1

    def start(self):
        eventlet.spawn_n(self.worker)
        if self.debug:
            eventlet.spawn_n(self.stats_print)
        if self.mgmt:
            eventlet.spawn_n(self.run_mgmt_server)
        while True:
            try:
                self.listener()
            except Exception as e:
                self.logger.error(e)


class StatsdLogd(Daemon):

    def run(self, conf):
        tap = StatsdLog(conf)
        tap.start()


def run_server():
    usage = '''
    %prog start|stop|restart [--conf=/path/to/some.conf] [--foreground|-f]
    '''
    args = optparse.OptionParser(usage)
    args.add_option('--foreground', '-f', action="store_true",
        help="Run in foreground")
    args.add_option('--conf', default="./statsdlogd.conf",
        help="path to config. default = ./statsdlogd.conf")
    options, arguments = args.parse_args()
    
    if len(sys.argv) <= 1:
        args.print_help()
    
    if options.foreground:
        conf = readconf(options.conf)
        tap = StatsdLog(conf['main'])
        tap.start()
        sys.exit(0)
    
    if len(sys.argv) >= 2:
        daemon = StatsdLogd('/tmp/statsdlogd.pid')
        if 'start' == sys.argv[1]:
            conf = readconf(options.conf)
            daemon.start(conf['main'])
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            args.print_help()
            sys.exit(2)
        sys.exit(0)
    else:
        args.print_help()
        sys.exit(2)

if __name__ == '__main__':
    run_server()
