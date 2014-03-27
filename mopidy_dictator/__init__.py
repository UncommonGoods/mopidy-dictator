from __future__ import unicode_literals

import os

from mopidy import config, ext


__version__ = '0.0.1' # HOW IS VERSION FORMED


class Extension(ext.Extension):

    dist_name = 'Mopidy-Dictator'
    ext_name = 'dictator'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['hostname'] = config.Hostname()
        schema['port'] = config.Port()
        schema['password'] = config.Secret(optional=True)
        schema['max_connections'] = config.Integer(minimum=1)
        schema['connection_timeout'] = config.Integer(minimum=1)
        schema['zeroconf'] = config.String(optional=True)

        # what to do when a bad word is encountered. either log it,
        # ignore the command, or both.
        schema['bad_word_action'] = config.String(optional=True,
                                                  choices=['log', 'deny', 'both'])
        # list of bad words to search commands for in regex format(?)
        schema['bad_words'] = config.List(optional=True)
        # list of ip:name pairs, or just ip
        schema['ip_list'] = config.List(optional=True)
        schema['disable_mute'] = config.Boolean()
        # where to log transgressions
        schema['log_file'] = config.Path(optional=True)
        # instead of using log_file, log transgressions in memory
        schema['log_memory'] = config.Boolean()
        # number of consecutive tracks a single IP can queue. 0 means no limit.
        schema['queue_limit'] = config.Integer(optional=True, minimum=0, maximum=20)

        # experimental... disable automatic playing from search.
        # have to prevent "playid" commands immediately following "addid" commands.
        # Not sure if this is robust or even worth it. Look into using
        # 'command_list_(begin|end)'
        schema['disable_autoplay'] = config.Boolean()

        # enable spotify integration
        schema['spotify_support'] = config.Boolean()
        schema['bad_word_case_insensitive'] = config.Boolean()

        # ???
        schema['special_sauce'] = config.String(optional=True)

        return schema

    def validate_environment(self):
        pass

    # def setup(self, registry):
    #     from .actor import DictatorFrontend
    #     registry.add('frontend', DictatorFrontend)

    def get_frontend_classes(self):
        from .actor import DictatorFrontend
        return [DictatorFrontend]
