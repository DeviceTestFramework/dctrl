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

import dctrl
import dctrl.command
import dctrl.expect.cliexpect as cliexpect

import time
import pexpect


class UBootCommand(dctrl.command.DctrlCommand):
    """Control U-Boot device."""

    def __init__(self):
        super(UBootCommand, self).__init__(UBootCommand, "uboot")

    def __call__(self, con):
        return super(UBootCommand, self).__call__(con)


class prompt(UBootCommand):
    """get prompt"""

    def __init__(self):
        super(prompt, self).__init__()
        self.setup_hooks.append(self.setup_prompt)
        self.add_timeout_argument(1)
        self.add_argument('--nokeypress', metavar='OPTION',
                          help="disable keypress if enabled")

    def run(self, con, config, args):
        timeout=args['timeout']
        c = config['command']['prompt']
        dctrl.logger.info('Looking for: %s', c)

        while (timeout > 0):
            s = 0
            while(s < 1):
                if not args['nokeypress']:
                    con.send('\x03')
                time.sleep(0.1)
                s+=0.1
            try:
                match = con.expect(c,1)
                if (match == 0):
                    dctrl.logger.debug('got prompt: %s', prompt)
                    return 0
            except pexpect.TIMEOUT:
                pass
            timeout=timeout-1
        return (1, "timeout waiting for prompt")


class cmd(UBootCommand):
    """run arbitrary U-Boot command"""

    def __init__(self):
        super(cmd, self).__init__()
        self.add_timeout_argument()
        self.add_argument('command', metavar='COMMAND',
                          help="the U-Boot command string to run"
                          " (quoting is needed if it contains spaces)")

    def run(self, con, config, args):
        return con.runcommand(args['command'], timeout=args['timeout'])


class reset(UBootCommand):
    """run U-Boot reset command"""

    def __init__(self):
        super(reset, self).__init__()

    def run(self, con, config, args):
        return con.runcommand('reset', waitForPrompt=False)


class boot(UBootCommand):
    """run U-Boot boot command"""

    def __init__(self):
        super(boot, self).__init__()

    def run(self, con, config, args):
        return con.runcommand('boot', waitForPrompt=False)
