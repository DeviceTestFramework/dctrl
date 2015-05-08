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

import serpexpect, telnetpexpect, sshpexpect, pexpect
import sys, re


def fixup_crlf(b):
    import re
    # sanitize \r\n mess a bit
    b = re.sub(r"\r*\n\r*", "\n", b)
    b = re.sub(r"\r+", "\n", b)
    return b

def fixup_ansiesc(b):
    import re
    # drop of ANSI escape code sequences
    b = re.sub("\x1b\[(.*?[@-~])", "", b)
    b = re.sub("\x1b([@-_])", "", b)
    return b

def fixup_asciictrl(b):
    import re
    # fixup ASCII control characters
    try:
        import curses.ascii
        def unctrl(matchobj):
            return curses.ascii.unctrl(matchobj.group(0))
    except ImportError:
        ctrlcharstr = ("^@", "^A", "^B", "^C", "^D", "^E", "^F", "^G", "^H",
                       "^I", "^J", "^K", "^L", "^M", "^N", "^O", "^P", "^Q",
                       "^R", "^S", "^T", "^U", "^V", "^W", "^X", "^Y", "^Z",
                       "^[", "^\\", "^]", "^^", "^_")
        def unctrl(matchobj):
            char = ord(matchobj.group(0))
            def _unctrl(char):
                if char < len(ctrlchars):
                    return ctrlcharstr[char]
                if char == '\x7f':
                    return "^?"
                if char >= 0x80:
                    return _unctrl(char - 0x80)
    b = re.sub("[\x00-\x08]|[\x0b-\x1f]|\x7f", unctrl, b)
    return b

class CLILogFile:

    closed = True
    buffer = ""

    def __init__(self, filename, port):
        if filename == "stdout":
            self.file = sys.stdout
        elif filename == "stderr":
            self.file = sys.stderr
        else:
            self.file = open(filename, "a")
        self.port = port
        self.closed = False
        return

    def __del__(self):
        if not self.closed:
            self.close()
        return

    def close(self):
        if self.file in (sys.stdout, sys.stderr):
            self.file.write(("-- logfile (%s) "%self.port).ljust(79, '-') + "\n")
        # sanitize \r\n mess a bit
        b = fixup_crlf(self.buffer)
        # drop terminating whitespace
        b = b.rstrip()
        # drop of ANSI escape code sequences
        b = fixup_ansiesc(b)
        # fixup ASCII control characters
        b = fixup_asciictrl(b)
        self.file.write(b)
        if self.file in (sys.stdout, sys.stderr):
            self.file.write("\n".ljust(80, '-') + "\n")
        else:
            self.file.write("\n\n")
            self.file.close()
        self.file = None
        self.buffer = ""
        self.closed = True
        return

    def write(self, s):
        self.buffer += s
        return

    def flush(self):
        return

class BaseCLI:

    output = None

    def __init__ (self, prompt='# ', linesep='\n', sendlinesep='\n',
                  verbose=False, logfile=None, port=''):

        self.prompt = prompt
        self.linesep = linesep
        self.sendlinesep = sendlinesep
        self.consume_command_echo = 0
        self.verbose = verbose > 1
        if logfile:
            self.logfile = CLILogFile(logfile, port)
            self.info("opened logfile %s"%logfile)
        return


    def __del__(self):
        return


    def set_prompt(self, prompt):
        self.prompt = prompt
        return


    def set_consume_command_echo(self, timeout):
        self.consume_command_echo = timeout
        return


    def log(self, s, append="\n"):
        if self.logfile:
            self.logfile.write(s + append)
        return


    def info(self, s, append="\n"):
        if self.verbose:
            print s + append,


    def error(self, s, append="\n"):
        print >> sys.stderr, "dctrl: error: " + s + append,


    def expectprompt(self, prompt=None, timeout=-1):

        if prompt == None:
            prompt = self.prompt

        try:
            self.expect(prompt, timeout)
        except pexpect.TIMEOUT, e:
            return False

        return True


    def sendline(self, s='', noLogSend=None):
        self.send(s, noLogSend)
        self.send(self.sendlinesep, noLogSend)
        return len(s) + len(self.sendlinesep)


    def flushinput(self):
        """Override this if there is a way to flush pending input"""

        return


    def runcommand(self, command, pattern=[], prompt=None, waitForPrompt=True,
                   timeout=-1, returnbool=True, expectNoOutput=False, cmdOutputFile=None):
        """Run a command, wait for it to ....  PRECONDITION: target is at prompt, ie. ready to accept commands.  Returns (command_completed, pattern_found, output)"""
        if self.verbose > 1:
            print self.verbose_prefix + command

        if(cmdOutputFile):
            self.logfile = CLILogFile(cmdOutputFile,0)
            self.info("opened cmd output file %s"%cmdOutputFile)

        self.output = None

        if prompt == None:
            prompt = self.prompt

        if not isinstance(pattern, list):
            if pattern:
                pattern = [pattern]
            else:
                pattern = []

        self.sendline(command)

        # Consume echo'ed command
        if self.consume_command_echo:
            self.logfile.write("cliexpect.py: consuming command echo. self.before: '%s' self.after: %s"%(self.before,self.after))
            try:
                self.expect_exact(command, self.consume_command_echo)
            except pexpect.TIMEOUT, e:
                print >>sys.stderr, "error: timeout 1 waiting for command echo"
                return False
            try:
                self.expect_exact(self.linesep, self.consume_command_echo)
            except pexpect.TIMEOUT, e:
                print >>sys.stderr, "error: timeout 2 waiting for command echo"
                return False
            if not self.before == "\r" * len(self.before):
                print >>sys.stderr, "error: bad command echo, expected '\r' got: '"+self.before+"'"


        if not waitForPrompt and not pattern:
            return True

        self.logfile.write("cliexpect.py: self.output before pattern match: %s\n"%(self.output))
        # look for pattern, prompt (if waitForPrompt) or timeout
        _pattern = pattern[:]
        _pattern.append(pexpect.TIMEOUT)
        if waitForPrompt:
            _pattern.append(prompt)
        index = self.expect(_pattern, timeout)
        self.pmatch = None
        self.output = self.before
        self.logfile.write("cliexpect.py: self.output after pattern match: %s\n"%(self.output))

        # timeout
        if index == len(pattern):
            self.logfile.write("cliexpect.py: Timeout in matching prompt '%s' or pattern '%s'. Timeout is %s\n"%(prompt,pattern[:], timeout))
            return None

        # matched prompt
        if index == (len(pattern) + 1):

            # command completed, without a pattern match
            if pattern:
                self.logfile.write("cliexpect.py: Failed to match pattern '%s' prior to getting the prompt '%s'\n"%(pattern[:],prompt))
                return False

            # command completed with no pattern to look for, so all is good
            else:
                def strip(s):
                    import re
                    # drop of ANSI escape code sequences
                    s = re.sub("\x1b\[(.*?[@-~])", "", s)
                    s = re.sub("\x1b([@-_])", "", s)
                    # drop terminating whitespace
                    s = s.strip()
                    # hrmpf, we even have to remove all linefeeds
                    s = s.translate(None, "\r\n")
                    return s
                if expectNoOutput and strip(self.before):
                    self.logfile.write("cliexpect.py: Expected NoOutput but got '%s'\n"%(strip(self.before)))
                    return False
                return True

        # a pattern matched
        self.pmatch = self.after
        self.output += self.after

        # don't wait for command to complete...
        if not waitForPrompt:
            return returnbool or index

        # FIXME: adjust timeout, subtracting time already spent waiting

        # wait for command to complete or timeout
        index2 = self.expect([pexpect.TIMEOUT, prompt], timeout)
        self.output += self.before

        # timeout
        if index2 == 0:
            self.logfile.write("Error (cliexpect.py): Timeout in getting a prompt after running the command (timeout is %s\n"%(timeout))
            return None

        # command completed
        return returnbool or index


class SerialCLI(BaseCLI, serpexpect.serspawn):


    def __init__ (self, port='/dev/ttyS0', baudrate=115200,
                  prompt='# ', linesep="\r\n", sendlinesep="\r\n",
                  verbose=False, verbose_prefix="SER> ",
                  logfile=None):

        serpexpect.serspawn.__init__(self, port, baudrate)
        self.verbose_prefix = verbose_prefix
        BaseCLI.__init__(self, prompt, linesep=linesep, sendlinesep=sendlinesep,
                         verbose=verbose, logfile=logfile, port=port)
        return


    def flushinput(self):

        self.flushInput()
        return


class TelnetCLI(BaseCLI, telnetpexpect.telnetspawn):


    def __init__ (self, host, port=23,
                  prompt="# ", linesep="\r\n", sendlinesep="\r\n",
                  verbose=False, verbose_prefix="Telnet> ", logfile=None):

        telnetpexpect.telnetspawn.__init__(self, host, port,
                                           sendlinesep=sendlinesep)
        self.verbose_prefix = verbose_prefix
        BaseCLI.__init__(self, prompt, linesep=linesep, sendlinesep=sendlinesep,
                         verbose=verbose, logfile=logfile,
                         port="%s:%s"%(host, port))
        return


    def flushinput(self):

        self.flush()
        return


class SshCLI(BaseCLI, sshpexpect.sshspawn):


    def __init__ (self, host, username, password, port=23,
                  prompt="# ", linesep="\r\n", sendlinesep="\r\n",
                  verbose=False, verbose_prefix="SSH> ", logfile=None):

        sshpexpect.sshspawn.__init__(self, host, username, password, port)
        self.verbose_prefix = verbose_prefix
        BaseCLI.__init__(self, prompt, linesep=linesep, sendlinesep=sendlinesep,
                         verbose=verbose, logfile=logfile,
                         port="%s@%s:%s"%(username, host, port))

        class PromptError(Exception):
            pass

        # Expect the prompt => ignoring the initial text send by the ssh connection
        if not BaseCLI.expectprompt(self, timeout=5):
            raise PromptError ("Failed to get a prompt '%s' within 5 s."%(self.prompt))

        return
