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

import dctrl
import dctrl.connection
import re
import traceback

class NoopArgumentParser(object):

    def __init__(self):
        self.defaults = {}

    def add_argument(self, *args, **kwargs):
        assert len(args) > 0
        if 'dest' in kwargs:
            name = kwargs[dest]
        elif not args[0].startswith('-'):
            name = args[0]
        else:
            name = None
            for arg in args:
                if arg.startswith('--'):
                    name = arg[2:]
                    break
            if name is None:
                assert args[0][0] == '-'
                name = args[0][1:]
            name = name.replace('-', '_')
        value = kwargs.get('default', None)
        self.defaults[name] = value

    def set_defaults(self, **kwargs):
        self.defaults.update(kwargs)

class NoopSubparsersAction(object):
    def __init__(self):
        pass
    def add_parser(self, *args, **kwargs):
        return NoopArgumentParser()

def run(cmd):
    from dctrl.config import config
    logger = dctrl.logger
    if config['command']['connection']:
        connection_type = config['command']['connection']['type']
        try:
            con = dctrl.connection.connect(connection_type)
        except Exception:
            logger.debug("connect failed", exc_info=True)
            raise
    else:
        con = None
    try:
        cmd.setup(con, config)
    except Exception as e:
        logger.debug("setup failed", exc_info=True)
        return (2, "%s: setup: %s"%(cmd.get_name(), e))
    try:
        ret = cmd(con)
        # Check for bool first since a bool is a subclass of int in python.
        if isinstance(ret, bool):
            if ret:
                ret = (0, "")
            else:
                ret = (1, "")
        elif isinstance(ret, int):
            ret = (ret, "")
        if not (isinstance(ret, tuple) and
                len(ret) == 2 and
                ret[0] in (0, 1, 2)):
            ret = (2, "%s: invalid return value: %s"%(cmd.get_name(), ret))
        if ret[0] is True:
            ret = (0, ret[1])
        elif ret[0] is False:
            ret = (1, ret[1])
        logger.debug("command result: %r", ret)
    except Exception as e:
        logger.debug("command failed", exc_info=True)
        return (2, "%s: Exception: %s \nStacktrace:\n %s"%(cmd.get_name(), e,traceback.format_exc()))
    finally:
        try:
            cmd.teardown(con, config)
        except Exception as e:
            logger.debug("teardown failed", exc_info=True)
            return (2, "%s: teardown: %s"%(cmd.get_name(), e))
    return ret


class CommandConfigError(Exception):
    pass


def get_command_group(cls, name):
    try:
        ret = dctrl._commands[name]
        assert cls == ret.cls
    except KeyError:
        dctrl._commands[name] = DctrlCommandGroup(cls, name)


class DctrlCommandGroup(object):

    def __init__(self, cls, name):
        self.cls = cls
        self.name = name
        if hasattr(dctrl, 'subparsers'):
            self.parser = dctrl.subparsers.add_parser(name, help=cls.__doc__)
            self.subparsers = self.parser.add_subparsers()
        else:
            self.parser = NoopArgumentParser()
            self.subparsers = NoopSubparsersAction()


class DctrlCommand(object):
    """Base class for dctrl commands.

    This must be subclassed for each command group.
    """

    epilog = None

    def __init__(self, group_cls, group_name, name=None):
        self.setup_hooks = []
        self.teardown_hooks = []
        if not hasattr(group_cls, '_group'):
            assert group_name not in dctrl._commands
            group_cls._group = DctrlCommandGroup(group_cls, group_name)
        if name:
            self.name = name
        elif not hasattr(self, 'name'):
            self.name = self.__class__.__name__.replace('_', '-')
        self.parser = self._group.subparsers.add_parser(
            self.name, description=self.__doc__, epilog=self.epilog)
        self.parser.set_defaults(run=self)

    def setup(self, con, config):
        for hook in self.setup_hooks:
            hook(con, config)

    def teardown(self, con, config):
        for hook in self.teardown_hooks:
            hook(con, config)

    def setup_consume_command_echo(self, con, config):
        con.set_consume_command_echo(1)

    def setup_prompt(self, con, config):
        c = config['command']
        if not 'prompt' in c or c['prompt'] is None:
            raise CommandConfigError("%s prompt must be configured"%(
                    self.get_group_name()))

    def __call__(self, con):
        dctrl.logger.debug("running command: %s"%(self.get_name()))
        from dctrl.config import config
        return self.run(con, config, config['params']) # 0=success, 1=failed, 2=dctrl error

    def add_argument(self, *args, **kwargs):
        return self.parser.add_argument(*args, **kwargs)

    def add_timeout_argument(self, default=1):
        return self.parser.add_argument(
            '--timeout', type=int, metavar='SECONDS', default=default,
            help="timeout (default: %(default)s)")

    def add_mac_address_argument(self):
        self.setup_hooks.append(self.check_mac_address)
        return self.parser.add_argument(
            'mac-address', metavar='MAC-ADDRESS',
            help="mac address")

    def check_mac_address(self, con, config):
        params = config['params']
        if params['mac-address'] is not None:
            if re.match(r"^([0-9a-fA-F]{2})(:[0-9a-fA-F]{2}){5}$", params['mac-address']):
                config['command']['mac-address'] = params['mac-address']
            else:
                raise dctrl.HookError("invalid mac address: %s"%params['mac-address'])
        else:
            raise dctrl.HookError("mac address must be given as argument")

    def add_eth_address_argument(self, default):
        self.setup_hooks.append(self.check_eth_address)
        return self.parser.add_argument(
            '--eth-address', metavar='ETH-ADDRESS', default=default,
            help="eth IP address")

    def check_eth_address(self, con, config):
        params = config['params']
        if params['eth_address'] is not None:
            if re.match(r"^([0-9]{1,3})(\.[0-9]{1,3}){3}$", params['eth_address']):
                config['command']['eth_address'] = params['eth_address']
            else:
                raise dctrl.HookError("invalid eth address: %s"%params['eth_address'])
        else:
            raise dctrl.HookError("eth address must be given as argument")

    def add_host_address_argument(self, default):
        self.setup_hooks.append(self.check_host_address)
        return self.parser.add_argument(
            '--host-address', metavar='HOST-ADDRESS', default=default,
            help="host IP address")

    def check_host_address(self, con, config):
        params = config['params']
        if params['host_address'] is not None:
            if re.match(r"^([0-9]{1,3})(\.[0-9]{1,3}){3}$", params['host_address']):
                config['command']['host_address'] = params['host_address']
            else:
                raise dctrl.HookError("invalid host address: %s"%params['host_address'])
        else:
            raise dctrl.HookError("host address must be given as argument")

    def add_netmask_argument(self, default):
        self.setup_hooks.append(self.check_netmask)
        return self.parser.add_argument(
            '--netmask', metavar='NETMASK', default=default,
            help="NETMASK")

    def check_netmask(self, con, config):
        params = config['params']
        if params['netmask'] is not None:
            if re.match(r"^([0-9]{1,3})(\.[0-9]{1,3}){3}$", params['netmask']):
                config['command']['netmask'] = params['netmask']
            else:
                raise dctrl.HookError("invalid netmask %s"%params['netmask'])
        else:
            raise dctrl.HookError("netmask must be given as argument")

    def get_group_name(self, upper=False):
        if upper:
            return self._group.name.upper()
        return self._group.name

    def get_cmd_name(self):
        return self.name

    def get_name(self):
        return "%s %s"%(self._group.name, self.name)

    def is_stub(self):
        return self.run is None
