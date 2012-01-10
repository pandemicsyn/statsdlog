import eventlet
from eventlet.green import socket
from eventlet.queue import Queue
from daemonutils import Daemon, readconf
from random import random
try:
    import simplejson as json
except ImportError:
    import json
from logging.handlers import SysLogHandler
import logging
from sys import maxint
import optparse
import sys
import re


class StatsdLog(object):

    def __init__(self, conf):
        TRUE_VALUES = set(('true', '1', 'yes', 'on', 't', 'y'))
        self.conf = conf
        self.logger = logging.getLogger('statsdLog')
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
            with open(self.patterns_file) as pfile:
                self.patterns = json.loads(pfile.read())
        except Exception as err:
            self.logger.critical(err)
            print err
            sys.exit(1)
        self.statsd_addr = (self.statsd_host, self.statsd_port)
        self.comp_patterns = {}
        for item in self.patterns:
            self.comp_patterns[item] = re.compile(self.patterns[item])

    def check_line(self, line):
        """
        Check if a line matches our search patterns.

        :param line: The string to check
        :returns: None or regex entry that matched
        """
        for entry in self.comp_patterns:
            if self.comp_patterns[entry].match(line):
                return entry
        return None

    def stats_print(self):
        """
        Periodically dump some stats to the logs.
        """
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
        """
        Fire event to statsd

        :param payload: The payload of the udp packet to send.
        """
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.sendto(payload, self.statsd_addr)
        except Exception:
            #udp sendto failed (socket already in use?), but thats ok
            self.logger.error("Error trying to send statsd event")

    def statsd_counter_increment(self, stats, delta=1):
        """
        Increment multiple statsd stats counters

        :param stats: list of stats items to package and send
        :param delta: delta of stats items
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

    def worker(self):
        """
        Check for and process log lines in queue
        """
        while True:
            msg = self.q.get()
            matched = self.check_line(msg)
            if matched:
                self.statsd_counter_increment([matched])
                if self.hits >= maxint:
                    self.logger.info("hit maxint, reset hits counter")
                    self.hits = 0
                self.hits += 1
            else:
                pass

    def listener(self):
        """
        syslog udp listener
        """
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
                    if self.counter >= maxint:
                        self.logger.info("hit maxint, reset seen counter")
                        self.counter = 0
                    self.counter += 1
                else:
                    if self.debug:
                        self.logger.notice("max log lines in queue, skipping")
                    if self.skip_counter >= maxint:
                        self.logger.info("hit maxint, reset skip counter")
                        self.skip_counter = 0
                    self.skip_counter += 1

    def start(self):
        """
        Start the listener, worker, and mgmt server.
        """
        eventlet.spawn_n(self.worker)
        if self.debug:
            eventlet.spawn_n(self.stats_print)
        while True:
            try:
                self.listener()
            except Exception as err:
                self.logger.error(err)


class StatsdLogd(Daemon):
    """
    Statsdlog Daemon
    """

    def run(self, conf):
        """
        Startup statsdlog server
        """
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
