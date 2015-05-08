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

import dctrl.command


class TestCommand(dctrl.command.DctrlCommand):
    """Dummy test commands."""

    def __init__(self):
        super(TestCommand, self).__init__(TestCommand, "test")

    def __call__(self, con):
        return super(TestCommand, self).__call__(con)


class success(TestCommand):
    """command that always succeeds"""

    def run(self, con, config, args):
        return 0

class failure(TestCommand):
    """command that always fails"""

    def run(self, con, config, args):
        return (1, "This is supposed to fail")
