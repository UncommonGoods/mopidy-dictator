from __future__ import unicode_literals

import logging
import re
import sqlite3
import urllib

from Queue import Queue
from mopidy.mpd import protocol
from . import dispatcher
from mopidy.utils import formatting, network
from mopidy.models import Artist, Album, Track, Playlist

logger = logging.getLogger(__name__)


class DictatorSession(network.LineProtocol):
    """
    The MPD client session. Keeps track of a single client session. Any
    requests from the client is passed on to the MPD request dispatcher.
    """

    terminator = protocol.LINE_TERMINATOR
    encoding = protocol.ENCODING
    delimiter = r'\r?\n'

    translator = None
    ip_list = {}
    recent_adds = None
    log_file = None

    # compiled regex
    addid = None
    local_re = None
    bad_words_re = []
    spotify_re = None

    def __init__(self, connection, config=None, core=None):
        super(DictatorSession, self).__init__(connection)
        self.dispatcher = dispatcher.DictatorDispatcher(
            session=self, config=config, core=core)
        conf = config['dictator']
        self.make_ip_list(conf)
        self.init_db(conf)
        self.compile_re(conf)
        if conf['queue_limit'] > 0:
            self.recent_adds = Queue(maxsize=conf['queue_limit'])
        if conf['spotify_support']:
            from mopidy_spotify import translator
            self.translator = translator
            logger.info('spotify support enabled in dictator')

    def compile_re(self, conf):
        ws = r'\b'
        mod = re.I if conf['bad_word_case_insensitive'] else None
        self.addid = re.compile(r'add(?:id)? "(.*)"', re.I)
        self.local_re = re.compile(r'^local:track:(.*)$', re.I)
        self.spotify_re = re.compile(r'spotify:', re.I)
        try:
            self.bad_words_re = [re.compile(ws+p+ws, mod) for p in conf['bad_words']]
        except Exception as e:
            logger.info('ERROR: BAD WORDS FAILED TO COMPILE: '+str(e))

    # TODO: make a decorator that does all the connection opening/closing boilerplate
    def init_db(self, conf):
        self.log_file = ':memory:' if conf['log_memory'] else conf['log_file']
        conn = sqlite3.connect(self.log_file)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS bad_songs (
                name TEXT,
                song TEXT,
                num INTEGER,
                modified DATETIME
            );
        """)
        conn.commit()
        conn.close()

    def log_play(self, song, name):
        conn = sqlite3.connect(self.log_file)
        c = conn.cursor()
        m = self.local_re.search(song)
        if m is not None: # fix up local tracks
            song = urllib.unquote(m.group(1))
        res = c.execute('SELECT num FROM bad_songs WHERE name=? AND song=?', (name, song)).fetchone()
        if res is None:
            c.execute("INSERT INTO bad_songs (name, song, num, modified) VALUES (?, ?, ?, DATETIME('now'))", (name, song, 1))
        else:
            c.execute("UPDATE bad_songs SET num=?, modified=DATETIME('now') WHERE name=? AND song=?", (res[0]+1, name, song))
        conn.commit()
        conn.close()
        
    # TODO: make this support IP only syntax: ip(:name)?
    def make_ip_list(self, conf):
        self.ip_list = {ip:name for ip, name in map(lambda x: x.split(':'), conf['ip_list'])}

    def remove_from_queue(self):
        self.recent_adds.get(True, 1)

    def add_to_queue(self, ip):
        if self.recent_adds.full():
            self.remove_from_queue()
        self.recent_adds.put(ip, True, 1)

    def on_start(self):
        logger.info('New Dictator connection from [%s]:%s', self.host, self.port)
        self.send_lines(['OK MPD %s' % protocol.VERSION])

    def on_line_received(self, line):
        logger.debug('Request from [%s]:%s: %s', self.host, self.port, line)

        dictator_res = self.dictator_filter(line, self.host)
        if dictator_res is not True:
            self.send_lines(dictator_res)
            return

        response = self.dispatcher.handle_request(line)
        if not response:
            return

        logger.debug(
            'Response to [%s]:%s: %s', self.host, self.port,
            formatting.indent(self.terminator.join(response)))

        self.send_lines(response)

    def get_ip_from_host(self, host):
        return host.split(':')[-1].replace(']', '')

    # returns True if the queue is filled entirely by adds from the 'search' ip
    def full_queue(self, search):
        if not self.recent_adds.full():
            return False
        for ip in self.recent_adds.queue:
            if search != ip:
                return False
        return True

    """
    TODO: this is all pretty specific to GMPC-styled requests.
    Make it use a more generic MPD protocol.

    TODO: break this down into several functions
    TODO: get command/error numbers from some pre-populated dict
    """
    def dictator_filter(self, line, host):
        ip = self.get_ip_from_host(host)
        ip_name = ip if ip not in self.ip_list else self.ip_list[ip]
        if line not in ('status', 'outputs'):
            logger.info("cmd: '%s' [%s]", line, ip)
        config = self.dispatcher.config['dictator']

        # disable mute
        if config['disable_mute'] and 'enableoutput "0"' in line:
            logger.info("MUTE REQUEST DENIED")
            return "ACK [50@1] {enableoutput} System mute disabled"

        # bad word filter
        match = self.addid.match(line)
        if  match is not None:
            logger.info("%s requested a new track", ip_name)
            filename = match.group(1)
            if len(config['bad_words']) > 0:
                logger.info('filtering bad words')
                logger.info("filename: "+filename)
                # translate spotify track ids to track names
                if config['spotify_support'] and self.spotify_re.match(filename) is not None:
                    if filename in self.translator.track_cache:
                        filename = self.translator.track_cache[filename].name
                        logger.info("spotify filename: "+filename)
                for pattern in self.bad_words_re:
                    if pattern.search(filename) is not None:
                        if config['bad_word_action'] in ('log', 'both'):
                            logger.info('saving to db: %s (%s)', filename, ip_name)
                            self.log_play(filename, ip_name)
                        if config['bad_word_action'] in ('deny', 'both'):
                            logger.info('ADDID DENIED FOR "%s"', filename)
                            return "ACK [50@1] {addid} song deemed inappropriate"
                        break

            if config['queue_limit']:
                if self.full_queue(ip):
                    # TODO: modify this behavior based on number of server connections
                    logger.info('track denied based on queue')
                    return "ACK [50@1] {addid} request limit exceeded"
                else:
                    self.add_to_queue(ip)
        return True

    def on_idle(self, subsystem):
        self.dispatcher.handle_idle(subsystem)

    def decode(self, line):
        try:
            return super(DictatorSession, self).decode(line.decode('string_escape'))
        except ValueError:
            logger.warning(
                'Stopping actor due to unescaping error, data '
                'supplied by client was not valid.')
            self.stop()

    def close(self):
        self.stop()
