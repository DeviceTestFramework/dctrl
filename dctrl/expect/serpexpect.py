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

import serial, pexpect
import time

class serspawn(serial.Serial, pexpect.spawn):

    closed = True

    def __init__ (self, port, baudrate=115200, bytesize=serial.EIGHTBITS,
                  parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                  readTimeout=0.1, writeTimeout=None, xonxoff=False, rtscts=False,
                  timeout=30, maxread=2000, searchwindowsize=None,
                  logfile=None):

        self.readTimeout = readTimeout
        serial.Serial.__init__(self, port=port, baudrate=baudrate,
                               bytesize=bytesize, parity=parity,
                               stopbits=stopbits, timeout=readTimeout,
                               xonxoff=xonxoff, rtscts=rtscts,
                               writeTimeout=writeTimeout)

        self.args = None
        self.command = None
        pexpect.spawn.__init__(self, None, None, timeout, maxread,
                               searchwindowsize, logfile)
        self.child_fd = -1
        self.own_fd = False
        self.closed = False
        self.name = '<serial port %s>' % port

        self.default_timeout = timeout

        return

    def __del__ (self):

        serspawn.close(self)
        return

    def close (self):

        if self.closed:
            return
        serial.Serial.close(self)
        self.closed = True
        return

    def flush (self):

        serial.Serial.flush(self)
        return

    def isatty (self):

        return False

    def isalive (self):

        return not self.closed

    def terminate (self, force=False):

        raise ExceptionPexpect ('This method is not valid for serial ports.')

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
        serial.Serial.write(self, s)
        return s

    def send(self, s, noSendLog=None):

        if noSendLog is not None:
            return self.send(s)
        else:
            time.sleep(self.delaybeforesend)
            serial.Serial.write(self, s)
            return s

    def read_nonblocking (self, size=1, timeout=-1):

        # FIXME: find out why timeout is broken in pyserial
        #if timeout != -1:
        #    self.timeout = 1
        self.timeout = self.readTimeout
        b = serial.Serial.read(self, size)
        self.timeout = self.default_timeout
        #if timeout != -1:
        #    self.timeout = self.default_timeout

        if self.logfile is not None:
            self.logfile.write(b)
            self.logfile.flush()
        if self.logfile_read is not None:
            self.logfile_read.write(b)
            self.logfile_read.flush()

        return str(b)
