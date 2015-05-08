#
# Copyright (C) 2015 Prevas A/S
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

import sys
import os
import logging
import imp
import inspect

import dctrl.command
import dctrl.config


def load_commands(path=os.environ.get('DCTRLPATH'), config_filename=None):
    if not hasattr(dctrl, '_commands'):
        dctrl._commands = {}

    if path:
        paths = path.split(':')
        logging.debug('paths : %s'%paths)
        clean_sys_path = sys.path
        for path in paths:
            if not os.path.isdir(path):
                logging.debug('skipping command search of non-existing dir: %s'
                              % path)
                continue
            logging.debug('path : %s'%path)
            top = os.path.abspath(path)
            logging.debug('top : %s'%top)
            sys.path.insert(0, top)
            commands = find_commands(top)
            sys.path = clean_sys_path
    elif config_filename:
        config = dctrl.config.get(config_filename)
        for module in config['commands'].keys():
            my_module = __import__(module)
            for cmd_name, cmd_cls in inspect.getmembers(my_module):
                import_commands(cmd_name, cmd_cls)
    else:
        raise Exception("please set DCTRLPATH")


def find_commands(top, path=[]):
    if path:
        d = os.path.join(top, os.path.join(*path))
    else:
        d = top
    for f in os.listdir(d):
        p = os.path.join(d, f)
        if os.path.isdir(p):
            if not os.path.isfile(os.path.join(p, '__init__.py')):
                continue
            name = '.'.join(path + [f])
            package = imp.find_module(f, [d])
            package = imp.load_module(name, *package)
            find_commands(top, path + [f])
        if os.path.isfile(p):
            (name, ext) = os.path.splitext(f)
            if not ext == '.py':
                continue
            if name.startswith('__'):
                continue
            module = imp.find_module(name, [d])
            name = '.'.join(path + [name])
            module = imp.load_module(name, *module)
            for cmd_name, cmd_cls in inspect.getmembers(module):
                import_commands(cmd_name, cmd_cls)


def import_commands(cmd_name, cmd_cls):
    if (
            inspect.isclass(cmd_cls) and
            issubclass(cmd_cls, dctrl.command.DctrlCommand) and
            hasattr(cmd_cls, 'run')
        ):
                # add command to command group, if not already added (by
                # another layer)
                cmd = cmd_cls()
                grp_name = cmd.get_group_name()
                if grp_name in dctrl._commands:
                    grp_cmds = dctrl._commands[grp_name]
                if not grp_name in dctrl._commands:
                    grp_cmds = dctrl._commands[grp_name] = {}
                if cmd.name not in grp_cmds:
                    grp_cmds[cmd.name] = cmd
