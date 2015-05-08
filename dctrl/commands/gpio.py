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

from linux import *

class GpioCommand(LinuxCommand):
    """
    GpioCommand is a common con
    """

class gpio_export(LinuxCommand):
    """
    gpio_export configure a gpio for usage
    """

    def __init__(self):
        LinuxCommand.__init__(self)
        self.add_argument('gpio', metavar='GPIO',
            help = "The gpio to export")

    def run(self, con, config, args):
        command = "echo %s > /sys/class/gpio/export"%(args['gpio'])
        if not con.runcommand(command):
             return (1, con.output.rstrip())
        return 0

class gpio_unexport(LinuxCommand):
    """
    gpio_unexport unexport a previously exported gpio
    """

    def __init__(self):
        LinuxCommand.__init__(self)
        self.add_argument('gpio', metavar='GPIO',
            help = "The gpio to unexport")

    def run(self, con, config, args):
        command = "echo %s > /sys/class/gpio/unexport"%(args['gpio'])
        if not con.runcommand(command):
             return (1, con.output.rstrip())
        return 0

class gpio_read(LinuxCommand):
    """
    gpio_read configures a gpio for input and returns it value.
    If an expected value is defined, the test will only pass if
    the read value is equal to the expected value
    """

    def __init__(self):
        LinuxCommand.__init__(self)
        self.add_argument('gpio', metavar='GPIO',
              help="The gpio to read")
        self.add_argument('expected', metavar='VALUE',
              help="Expected value to be read", nargs='?')

    def run(self, con, config, args):

        command = "echo in > /sys/class/gpio/gpio%s/direction"%(args['gpio'])
        if not con.runcommand(command):
            return (1, con.output.rstrip())

        command = "cat /sys/class/gpio/gpio%s/value"%(args['gpio'])
        if not con.runcommand(command):
            return (1, con.output.rstrip())

        output = con.output.rstrip()
        if not args['expected'] is None:
            if not args['expected'] == output:
                return (1, "Unexpected value (read %s, expected %s)"%(output, args['expected']))

        return True, output

class gpio_write(LinuxCommand):
    """
    gpio_write sets a gpio to output and assigns the value specified
    """

    def __init__(self):
        LinuxCommand.__init__(self)
        self.add_argument('gpio', metavar='GPIO',
              help="The gpio to write to")
        self.add_argument('value', metavar='VALUE',
              help="The value to set")

    def run(self, con, config, args):
        command = "echo out > /sys/class/gpio/gpio%s/direction"%(args['gpio'])
        if not con.runcommand(command):
            return (1, con.output.rstrip())

        command = "echo %s > /sys/class/gpio/gpio%s/value"%(args['value'],args['gpio'])
        if not con.runcommand(command):
            return (1, con.output.rstrip())

        return True
