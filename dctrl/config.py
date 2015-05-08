#
# Copyright (C) 2015  Prevas A/S
#
# This file is part of dctrl, an embedded device control framework
#
# dctrl is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# dctrl is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
# more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

import os
import yaml
import logging

import dctrl

logger = logging.getLogger("dctrl")

class ConfigError(Exception):
    pass


config = None


def load(filename, cmd):
    import dctrl.connection

    config = get(filename)
    config = env_override(config)

    cmd_group = cmd.get_group_name()
    if not cmd_group in config['commands']:
        raise ConfigError("invalid dctrl configuration",
                          "no %s commands definition"%(cmd_group))
    command_config = config['commands'][cmd_group]
    if not 'connection' in command_config:
        raise ConfigError("invalid dctrl configuration",
                          "%s connection not defined"%(cmd_group))
    connection_config = command_config['connection']
    if connection_config == 'none':
        command_config['connection'] = connection_config = {}
    else:
        if not 'type' in connection_config:
            raise ConfigError("invalid dctrl configuration",
                              "%s connection type not defined"%(cmd_group))
        connection_type = connection_config['type']
        if not dctrl.connection.is_valid_type(connection_type):
            raise ConfigError(
                "invalid dctrl configuration",
                "%s connection type not supported"%(connection_type))

    def getcattr(name, default=None, unescape=False, required=False):
        assert isinstance(name, basestring)
        try:
            val = connection_config[name]
        except KeyError:
            try:
                val = command_config[name]
            except KeyError:
                if required:
                    raise ConfigError(required)
                return default
        if unescape and isinstance(val, basestring):
            return eval("'%s'"%(val))
        else:
            return val

    command_config['prompt'] = getcattr(
        'prompt')
    command_config['linesep'] = getcattr(
        'linesep', default='\r\n', unescape=True)
    command_config['sendlinesep'] = getcattr(
        'sendlinesep', default=command_config['linesep'], unescape=True)

    assert not 'command' in config
    config['command'] = command_config
    del config['commands']
    del config['connections']
    globals()['config'] = config
    return


def get(filename):
    # Normalize the filename prior to checking existences
    filename=os.path.normpath(filename)
    if not os.path.exists(filename):
        raise ConfigError("dctrl configuration file not found",
                          str(filename))
    with open(filename, 'r') as config_file:
        config = yaml.load(config_file)
    if not 'commands' in config:
        raise ConfigError("invalid dctrl configuration",
                          "no commands defined")
    return config


def env_override(config, env_keys={}, parents=list()):
    """
    searches for yaml entries beginning with 'env-<match>' and overrides
    the value of <match> variables with the value loaded from the environment.

    config: the config to search and override
    env_keys: the <match> part of found entries beginning with 'env-'
    parents: current level of given config (used for printing overridings)
    """
    # look for env-vars at this level
    for key in config:
        if not key.startswith("env"):
            continue

        env_keys[key[4:]] = config[key]

    # for each entry at this level
    for key,val in config.items():
        # recurse into lower level while keeping existing env-vars
        if isinstance(val, dict):
            config[key] = env_override(val, env_keys, parents + [key])

        # replace vars with existing env-vars
        if key in env_keys and env_keys[key] in os.environ:
            logger.debug("replace {}.{} with {}".format(".".join(parents), key, env_keys[key]))
            config[key] = os.environ[env_keys[key]]

    # return modified config to higher levels
    return config
