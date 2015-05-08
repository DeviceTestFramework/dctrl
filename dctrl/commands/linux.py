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
import pexpect
import re
import argparse
import time
import os
import string

import dctrl
import dctrl.command
import dctrl.expect.cliexpect as cliexpect
import logging

logger = logging.getLogger("dctrl")

class LinuxCommand(dctrl.command.DctrlCommand):
    """Control Linux device."""

    # In order make it check the exit-code of the command on target set e.g.
    # self.add_allowed_exitcode_argument(default=[0])

    def __init__(self):
        super(LinuxCommand, self).__init__(LinuxCommand, "linux")
        self.setup_hooks.append(self.setup_prompt)
        self.setup_hooks.append(self.setup_consume_command_echo)
        self.waitForPrompt = True

    def __call__(self, con):
        from dctrl.config import config
        ret = super(LinuxCommand, self).__call__(con)
        # we do not only return integers anymore, also bool and tuple
        # convert to tuple to simplify check
        # Check for bool first since a bool is a subclass of int in python.
        if isinstance(ret, bool):
            if ret:
                ret = (0, "")
            else:
                ret = (1, "")
        elif isinstance(ret, int):
            ret = (ret, "")
        elif isinstance(ret, tuple):
            # Be sure to have ret[0] as an int!
            if isinstance(ret[0], bool):
                if ret[0]:
                    ret=(0,) + ret[1:]
                else:
                    ret=(1,) + ret[1:]

        # Sanity checks on how ret must look
        if not (isinstance(ret, tuple) and
                len(ret) == 2):
            raise TypeValError("Only accepting tuples of length 2 and the first element must be an int. First element means 0=> OK")
        if not type(ret[0]) == int:
            raise TypeValError("ret[0] must be an int here - I do not know how to handle this!!!")

        allowed_exitcodes = config['params'].get('allowed_exitcodes', None)
        if ret[0] == 0 and allowed_exitcodes and self.waitForPrompt:
            cret = con.runcommand('echo $?',
                                 pattern='^[1-2]?[0-9]{1,2}%s'%(con.linesep),
                                 timeout=1)
            if not cret:
                return (1, "exitcode not found")
            try:
                exitcode = int(con.pmatch)
            except ValueError:
                return (1, "invalid exitcode: %s"%(cret))
            if not exitcode in allowed_exitcodes:
                return (1, "bad exitcode: %s (allowed: %s)"%(
                        exitcode, ','.join(map(str, allowed_exitcodes))))
        return ret

    class ExitCodeAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if not values:
                setattr(namespace, self.dest, None)
                return
            allowed_exitcodes = []
            for exitcode in values.split(','):
                try:
                    allowed_exitcodes.append(int(exitcode))
                except ValueError:
                    raise argparse.ArgumentTypeError(
                        "bad exitcode: %r in %r"%(exitcode, values))
            setattr(namespace, self.dest, allowed_exitcodes)

    def add_allowed_exitcode_argument(self, default=None):
        return self.parser.add_argument(
            '--allowed-exitcodes', action=self.ExitCodeAction, default=default,
            metavar='INTEGERS',
            help="comma separated list of allowed exitcodes")

    def add_root_password_argument(self):
        self.setup_hooks.append(self.setup_root_password)
        return self.parser.add_argument(
            '--root-password', metavar='PASSWORD',
            help="target root password (not needed for ssh connections)")

    def setup_root_password(self, con, config):
        params = config['params']
        if params['root_password'] is not None:
            config['command']['root-password'] = params['root_password']
        elif config['command'].get('root-password', None) is None:
            raise dctrl.HookError(
                "root-password must be configured or given as argument")

    def runcommand_checkexit(self,connection, command, pattern=[], prompt=None,timeout=-1,
                             returnbool=True, expectNoOutput=False, cmdOutputFile=None, allowed_exitcodes=[0]):

        # Input checks allowed_exitcodes must be a list
        # If you do not what to check the exit code then use con.runcommand instead
        if not isinstance(allowed_exitcodes,list):
            connection.error("allowed_exitcodes must be a list! Current content: %s\n"%(allowed_exitcodes))
            return False

        # Call connections run command with waitForPrompt set to True
        ret = connection.runcommand(command, pattern, prompt, True,timeout, returnbool, expectNoOutput, cmdOutputFile)

        if ret == True:
            # Check the return code if the first command went well
            cret = connection.runcommand('echo $?',
                               pattern='^[1-2]?[0-9]{1,2}%s'%(connection.linesep),
                                   timeout=1, cmdOutputFile=cmdOutputFile)
            if not cret:
                connection.error("Could not get the exitcode from echo $?")
                return False
            try:
                exitcode = int(connection.pmatch)
            except ValueError:
                connection.error("invalid exitcode: %s\n"%(cret))
                return False
            if not exitcode in allowed_exitcodes:
                connection.error("bad exitcode: %s (allowed: %s)\n"%(
                    exitcode, ','.join(map(str, allowed_exitcodes))))
                return False

        return ret

def get_to_prompt(con, config, args, target='prompt'):
    username = config.get('username', 'root')

    prompts = {}

    if 'enter-prompt' in config:
        prompts['enter_prompt'] = config['enter-prompt']
    def enter_prompt():
        con.sendline('')

    if 'login-prompt' in config:
        prompts['login_prompt'] = config['login-prompt']
    def login_prompt():
        con.sendline(username)

    if 'password' in config:
        password = config['password']
        prompts['password_prompt'] = "Password: "
    def password_prompt():
        con.sendline(password)

    if 'root-prompt' in config:
        prompts['root_prompt'] = config['root-prompt']
    def root_prompt():
        con.set_prompt(config['root-prompt'])

    if 'prompt' in config:
        prompts['prompt'] = config['prompt']
    def prompt():
        con.set_prompt(config['prompt'])
        if target != 'root-prompt':
            return
        if not 'root-password' in config:
            print >>sys.stderr, "DEBUG: no root password"
            return None
        con.sendline('su')
        try:
            con.expect('Password: ', timeout=1)
        except pexpect.TIMEOUT, e:
            print >>sys.stderr, "error: timeout waiting for su password prompt"
            con.send('\x03')
            con.expect(config['prompt'], timeout=1)
            raise e
        con.sendline(config['root-password'])
        try:
            con.expect(config['root-prompt'], timeout=1)
        except pexpect.TIMEOUT, e:
            print >>sys.stderr, "error: timeout waiting for root prompt"
            con.send('\x03')
            try:
                con.expect(config['prompt'], timeout=1)
            except pexpect.TIMEOUT, e:
                con.send('\x04')
                try:
                    con.expect(config['prompt'], timeout=1)
                except pexpect.TIMEOUT, e:
                    print >>sys.stderr, "error: root prompt mess!"
                    raise e
            raise e
        con.set_prompt(config['root-prompt'])
        return 'root_prompt'

    # return to known state by (potentionally) logging out
    _console_state = None
    for breakchar in '\x03\x04': # Ctrl-C Ctrl-D
        con.send(breakchar)
        match = con.expect(
            prompts.values() + [pexpect.TIMEOUT], timeout=2)
        if match < len(prompts.keys()):
            prompt_func = eval(prompts.keys()[match])
            _console_state = prompt_func() or prompt_func.__name__
            break

    if _console_state is None:
        print >>sys.stderr, "error: unable to get a Linux prompt"
        return None

    attempts = 5
    while _console_state != target and attempts:
        attempts -= 1
        try:
            match = con.expect(prompts.values(), timeout=2)
        except pexpect.TIMEOUT, e:
            print >>sys.stderr, "timeout in state %s"%(_console_state)
            _console_state = None
            break
        prompt_func = eval(prompts.keys()[match])
        _console_state = prompt_func() or prompt_func.__name__

    return _console_state


class su_prompt(LinuxCommand):
    """get and initialize shell prompt with super-user permissions"""

    def __init__(self):
        super(su_prompt, self).__init__()
        self.add_root_password_argument()
        self.add_argument('--init-command', metavar='STRING',
                          help="shell command string to initialize the shell")

    def run(self, con, config, args):
        prompt = get_to_prompt(con, config['command'], args,
                               target='root_prompt')
        dctrl.logger.debug('got prompt: %s', prompt)

        init_command = args.get('init_command', None)
        if init_command is None:
            init_command = config.get('init-command',
                                      'stty cols 1000;dmesg -n 1')
        if not con.runcommand(init_command, expectNoOutput=True):
            return (1, "initialization command failed")
        return 0


class user_prompt(LinuxCommand):
    """get and initialize shell prompt"""

    def __init__(self):
        super(user_prompt, self).__init__()
        self.add_argument('--init-command', metavar='STRING',
                          help="shell command string to initialize the shell")

    def run(self, con, config, args):
        prompt = get_to_prompt(con, config['command'], args)
        dctrl.logger.debug('got prompt: %s', prompt)

        init_command = args.get('init_command', None)
        if init_command is None:
            init_command = config.get('init-command',
                                      'stty cols 1000;dmesg -n 1')
        if not con.runcommand(init_command, expectNoOutput=True):
            return (1, "initialization command failed")
        return 0


class cmd(LinuxCommand):
    """run arbitrary Linux command"""

    def __init__(self):
        super(cmd, self).__init__()
        self.add_timeout_argument(default=10)
        self.add_allowed_exitcode_argument(default=[0])
        self.add_argument('command', metavar='COMMAND',
                          help="the shell command string to run"
                          " (quoting is needed if it contains spaces)")
        self.add_argument('--no-wait', metavar='NOWAIT',
                          help="If enabled, do not wait for a prompt"
                          " and check command exit status")

    def run(self, con, config, args):
        if(args['no_wait']):
            self.waitForPrompt = False
        else:
            # Default always wait for prompt (and check and thereby also check the exit code
            self.waitForPrompt = True

        if('logfile' in args):
            ret = con.runcommand(args['command'], timeout=args['timeout'], cmdOutputFile=args['logfile'])
        else:
            ret = con.runcommand(args['command'], timeout=args['timeout'])
        return int(bool(not ret)), con.output


class linux_info(LinuxCommand):
    """Returns info about the running linux"""

    def __init__(self):
        super(linux_info,self).__init__()

    def run(self, con, config, args):
        result = {}
        if not con.runcommand("uname -r", timeout=10):
            return False
        result['osrelease'] = con.output.rstrip()

        if not con.runcommand("uname -m", timeout=10):
            return False
        result['machine'] = con.output.rstrip()

        if not con.runcommand("uname -v", timeout=10):
            return False
        result['version'] = con.output.rstrip()

        return True, result

class readonly(LinuxCommand):
    """Check if rootfs is mounted readonly"""

    def __init__(self):
        super(readonly, self).__init__()
        self.add_timeout_argument(default=10)
        self.add_argument('ro', metavar='COMMAND',
                          help="readonly in fstab")

    def run(self, con, config, args):
        if not con.runcommand("mount | head -n 1 | grep \"(%s)\""%(args['ro']), args['ro'], timeout=args['timeout']):
            return 1
        return 0

class modprobe(LinuxCommand):
    """Load a kernel module using modprobe"""

    def __init__(self):
        super(modprobe, self).__init__()
        self.add_timeout_argument(default=10)
        self.add_allowed_exitcode_argument(default=[0])
        self.add_argument('module', metavar='MODULE',
                          help="the name of the module to load")
        self.add_argument('--module-options', metavar='MODOPTS',
                          help="set module options when loading:"
                          " 'opt1=val1 opt2=val2'"
                          " (quoting is needed if it contains spaces)")
        self.add_argument('--unload', metavar='UNLOAD',
                          help="unload the specified module")

    def run(self, con, config, args):
        cmd = "modprobe "
        if(args['unload']):
            cmd = cmd + "-r "
        cmd = cmd + args['module']
        if('module-options' in args):
           cmd = cmd + " "+args['module-options']
        if('logfile' in args):
            ret = con.runcommand(cmd, timeout=args['timeout'], cmdOutputFile=args['logfile'])
        else:
            ret = con.runcommand(cmd, timeout=args['timeout'])
        if(con.output):
            #busybox modprobe returns 0 even if module could not be loaded
            #but outputs an error msg.
            return False,con.output
        return int(bool(not ret)), con.output
