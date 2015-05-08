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

"""This is like pexpect, but working on an internal ssh connection."""

import paramiko
import pexpect
import time

class sshspawn(pexpect.spawn):

    closed = True


    def __init__ (self, host, username, password, port=23, timeout=30,
                  maxread=2000, connect_timeout=10,
                  searchwindowsize=None, logfile=None, sendlinesep="\r\n"):

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, port, username, password,
                         timeout=connect_timeout, allow_agent=False,
                         look_for_keys=False)
        self.sshch = self.ssh.invoke_shell(width=400)
        self.sendlinesep = sendlinesep

        self.args = None
        self.command = None
        pexpect.spawn.__init__(self, None, None, timeout, maxread,
                               searchwindowsize, logfile)
        self.child_fd = -1
        self.own_fd = False
        self.closed = False
        self.name = '<ssh connection %s@%s:%d>'%(username, host, port)

        return


    def __del__ (self):

        sshpexpect.close(self)
        self.logfile.write("\n")
        return


    def close (self):

        if self.closed:
            return
        self.sshch.close()
        self.ssh.close()
        self.closed = True
        return


    def isatty(self):

        return not self.closed


    def isalive(self):

        return not self.closed


    def fileno(self):
        if self.closed:
            return None
        return self.sshch.fileno()


    def terminate(self, force=False):

        raise ExceptionPexpect ('This method is not valid for ssh connections.')


    def kill(self, sig):

        return


    def send(self, s):

        time.sleep(self.delaybeforesend)

        if self.logfile is not None:
            self.logfile.write (s)
            self.logfile.flush()
        if self.logfile_send is not None:
            self.logfile_send.write (s)
            self.logfile_send.flush()

        self.sshch.setblocking(1)
        return self.sshch.send(s)

    def send(self, s, noSendLog=None):

        if noSendLog is not None:
            return self.send(s)
        else:
            time.sleep(self.delaybeforesend)
            self.sshch.setblocking(1)
            return self.sshch.send(s)


    def read_nonblocking (self, size=1, timeout=-1):
        import socket

        if timeout == -1:
            timeout = self.timeout

        if timeout:
            self.sshch.setblocking(0)
        self.sshch.settimeout(timeout)

        try:
            buf = self.sshch.recv(size)
        except socket.timeout, e:
            raise pexpect.TIMEOUT("Timeout in sshpexpect.read_nonblocking")

        if self.logfile is not None:
            self.logfile.write(buf)
            self.logfile.flush()
        if self.logfile_read is not None:
            self.logfile_read.write(buf)
            self.logfile_read.flush()

        return buf
