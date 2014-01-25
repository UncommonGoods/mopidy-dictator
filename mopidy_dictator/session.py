from __future__ import unicode_literals

import logging
import re

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
    addid = re.compile(r'^addid "(.*)"$', re.I)

    def __init__(self, connection, config=None, core=None):
        super(DictatorSession, self).__init__(connection)
        self.dispatcher = dispatcher.DictatorDispatcher(
            session=self, config=config, core=core)
        if config['dictator']['spotify_support']:
            from mopidy_spotify import translator
            self.translator = translator
            logger.info('spotify support enabled in dictator')

    def on_start(self):
        logger.info('New Dictator connection from [%s]:%s', self.host, self.port)
        self.send_lines(['OK MPD %s' % protocol.VERSION])

    def on_line_received(self, line):
        logger.debug('Request from [%s]:%s: %s', self.host, self.port, line)

        if not self.dictator_filter(line, self.host):
            self.send_lines(" ") # TODO: some kind of standard 'null' response?
            return

        response = self.dispatcher.handle_request(line)
        if not response:
            return

        logger.debug(
            'Response to [%s]:%s: %s', self.host, self.port,
            formatting.indent(self.terminator.join(response)))

        self.send_lines(response)

    """
    TODO: this is all pretty specific to GMPC-styled requests.
    Make it use a more generic MPD protocol.

    TODO: break this down into several functions
    """
    def dictator_filter(self, line, host):
        if line not in ('status', 'outputs'):
            logger.info("cmd: '%s' [%s]", line, host)
        config = self.dispatcher.config['dictator']

        # disable mute
        if config['disable_mute'] and 'enableoutput "0"' in line:
            logger.info("MUTE REQUEST DENIED")
            return False

        # bad word filter
        if len(config['bad_words']) > 0 and re.match(r'addid ', line) is not None:
            logger.info('filtering bad words')
            match = self.addid.search(line)
            if match is not None:
                filename = match.group(1)
                logger.info("filename: "+filename)
                # translate spotify track ids to track names
                if config['spotify_support'] and re.match(r'spotify:', filename) is not None:
                    if filename in self.translator.track_cache:
                        filename = self.translator.track_cache[filename].name
                        logger.info("spotify filename: "+filename)
            for pattern in config['bad_words']:
                try:
                    word_pattern = r'\b' + pattern + r'\b'
                    logger.info("trying: '%s'", word_pattern)
                    regex = re.compile(word_pattern, re.I) # TODO: make case insensitivity optional?
                    if regex.search(filename) is not None:
                        if config['bad_word_action'] in ('deny', 'both'):
                            logger.info('ADDID DENIED FOR "%s"', filename)
                            return False
                        break
                except Exception:
                    logger.info('regex compilation FAILED')
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
