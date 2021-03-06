from __future__ import unicode_literals

import logging
import sys

import pykka

# from mopidy import zeroconf
from mopidy.core import CoreListener
from . import session
from mopidy.utils import encoding, network, process

logger = logging.getLogger(__name__)


class DictatorFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super(DictatorFrontend, self).__init__()

        hostname = network.format_hostname(config['dictator']['hostname'])
        self.hostname = hostname
        self.port = config['dictator']['port']
        # self.zeroconf_name = config['dictator']['zeroconf']
        # self.zeroconf_service = None

        try:
            network.Server(
                self.hostname, self.port,
                protocol=session.DictatorSession,
                protocol_kwargs={
                    'config': config,
                    'core': core,
                },
                max_connections=config['dictator']['max_connections'],
                timeout=config['dictator']['connection_timeout'])
        except IOError as error:
            logger.error(
                'Dictator server startup failed: %s',
                encoding.locale_decode(error))
            sys.exit(1)

        logger.info('Dictator server running at [%s]:%s', self.hostname, self.port)

    # def on_start(self):
    #     if self.zeroconf_name:
    #         self.zeroconf_service = zeroconf.Zeroconf(
    #             stype='_mpd._tcp', name=self.zeroconf_name,
    #             host=self.hostname, port=self.port)

    #         if self.zeroconf_service.publish():
    #             logger.info('Registered Dictator with Zeroconf as "%s"',
    #                         self.zeroconf_service.name)
    #         else:
    #             logger.info('Registering Dictator with Zeroconf failed.')

    def on_stop(self):
        # if self.zeroconf_service:
        #     self.zeroconf_service.unpublish()

        process.stop_actors_by_class(session.DictatorSession)

    def send_idle(self, subsystem):
        listeners = pykka.ActorRegistry.get_by_class(session.DictatorSession)
        for listener in listeners:
            getattr(listener.proxy(), 'on_idle')(subsystem)

    def playback_state_changed(self, old_state, new_state):
        self.send_idle('player')

    def tracklist_changed(self):
        self.send_idle('playlist')

    def options_changed(self):
        self.send_idle('options')

    def volume_changed(self, volume):
        self.send_idle('mixer')

    def mute_changed(self, mute):
        self.send_idle('output')
