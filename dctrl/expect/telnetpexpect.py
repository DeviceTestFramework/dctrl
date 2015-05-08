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

"""This is like pexpect, but working on an internal (py)serial connection."""

from telnetlib import Telnet
import pexpect
import time
import re

class telnetspawn(pexpect.spawn):

    closed = True
    readahead = 16
    readahead_buf = ''

    def __init__ (self, host, port=23, timeout=30, maxread=2000,
                  searchwindowsize=None, logfile=None, sendlinesep="\r\n"):

        self.telnet = Telnet(host, port)
        self.sendlinesep = sendlinesep

        self.args = None
        self.command = None
        pexpect.spawn.__init__(self, None, None, timeout, maxread,
                               searchwindowsize, logfile)
        self.child_fd = -1
        self.own_fd = False
        self.closed = False
        self.name = '<telnet connection %s:%d>'%(host, port)

        self.default_timeout = timeout

        return

    def __del__ (self):
        telnetspawn.close(self)
        self.logfile.write("\n")
        return

    def close (self):

        if self.closed:
            return
        self.telnet.close()
        self.closed = True
        return

    def flush (self):

        while len(self.telnet.read_eager()) > 0:
            continue
        return

    def isatty (self):

        return False

    def isalive (self):

        return not self.closed

    def terminate (self, force=False):

        raise ExceptionPexpect ('This method is not valid for telnet connections.')

    def kill (self, sig):

        return

    def send(self, s):

        time.sleep(self.delaybeforesend)
        if self.logfile is not None:
            self.logfile.write (s)
            self.logfile.flush()
        if self.logfile_send is not None:
            self.logfile_send.write (s)
            self.logfile_send.flush()
        self.telnet.write(s)
        return s

    def send(self, s, noSendLog=None):

        if noSendLog is not None:
            self.send(s)
        else:
            time.sleep(self.delaybeforesend)
            self.telnet.write(s)
        return s

    def read_nonblocking (self, size=1, timeout=-1):

        if timeout != -1:
            self.timeout = timeout

        buf = self.readahead_buf
        self.readahead_buf = ''

        # FIXME: update timeout during this loop!!

        more = self.telnet.read_eager()
        while len(more) > 0:
            buf += more
            more = self.telnet.read_eager()

        if len(buf) <= size:

            if self.logfile is not None:
                self.logfile.write(buf)
                self.logfile.flush()
            if self.logfile_read is not None:
                self.logfile_read.write(buf)
                self.logfile_read.flush()

            return buf

        self.readahead_buf = buf[size:]
        buf = buf[:size]

        if timeout != -1:
            self.timeout = self.default_timeout

        if self.logfile is not None:
            self.logfile.write(buf)
            self.logfile.flush()
        if self.logfile_read is not None:
            self.logfile_read.write(buf)
            self.logfile_read.flush()

        return buf
