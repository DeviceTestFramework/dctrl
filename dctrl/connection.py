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

import sys
import os
import logging

import dctrl.expect.cliexpect as cliexpect


def is_valid_type(connection_type):
    return connection_type in _connection_types

def connect(connection_type):
    return _connection_types[connection_type]()

def disconnect(connection):
    connection.close()

#    cli = connect(cmd_module, parser, cmd, cmd_name,
#                  options, subcmd_args, config, run, cleanup)
#
#    cli.close()


class ConnectionError(Exception):
    pass
class ConnectionConfigError(ConnectionError):
    pass


def connect_serial():
    import dctrl.config
    config = dctrl.config.config
    args = config['params']
    c = config['command']['connection']
    try:
        port = c['port']
    except KeyError:
        raise ConnectionConfigError("serial port not defined")
    try:
        baudrate = int(c['baudrate'])
    except KeyError:
        raise ConnectionConfigError("serial baudrate not defined")
    except ValueError:
        raise ConnectionConfigError(
            "invalid baudrate value: %s"%(c['baudrate']))

    try:
        cli = cliexpect.SerialCLI(
            port=port, baudrate=baudrate,
            prompt=config['command']['prompt'],
            linesep=config['command']['linesep'],
            sendlinesep=config['command']['sendlinesep'],
            verbose=((50 - dctrl.logger.getEffectiveLevel()) / 20),
            verbose_prefix=args['run'].get_group_name(upper=True) + "> ",
            logfile=args.get('logfile', None))
    except Exception, e:
        raise ConnectionError("serial connection to %s failed: %s"%(port, e))
    cli.log("dctrl: opened serial port %s connection"%(port))
    return cli


def connect_telnet():
    import socket, time

    import dctrl.config
    config = dctrl.config.config
    args = config['params']
    c = config['command']['connection']
    try:
        address = c['address']
    except KeyError:
        raise ConnectionConfigError("telnet address not defined")
    try:
        port = int(c['port'])
    except KeyError:
        port = 23
    except ValueError:
        raise ConnectionConfigError(
            "invalid port value: %s"%(c['port']))
    try:
        retry = float(c['retry'])
    except KeyError:
        retry = 0
    except ValueError:
        raise ConnectionConfigError(
            "invalid retry value: %s"%(c['retry']))
    try:
        retries = int(c['retries'])
    except KeyError:
        retries = 1
    except ValueError:
        raise ConnectionConfigError(
            "invalid retries value: %s"%(c['retries']))

    cli = None
    for i in range(retries, -1, -1):
        try:
            cli = cliexpect.TelnetCLI(
                address, port,
                prompt=config['command']['prompt'],
                linesep=config['command']['linesep'],
                sendlinesep=config['command']['sendlinesep'],
                verbose=((50 - dctrl.logger.getEffectiveLevel()) / 20),
                verbose_prefix=args['run'].get_group_name(upper=True) + "> ",
                logfile=args.get('logfile', None))
            break
        except socket.error, e:
            if i > 0:
                time.sleep(retry)
                continue
            raise ConnectionError(
                "telnet connection to %s:%d failed: %s"%(address, port, e))
    cli.log("dctrl: opened telnet connection to %s:%d"%(address, port))
    return cli


def connect_ssh():
    import dctrl.config
    config = dctrl.config.config
    args = config['params']
    c = config['command']['connection']
    try:
        address = c['address']
    except KeyError:
        raise ConnectionConfigError("ssh address not defined")
    try:
        username = c['username']
    except KeyError:
        raise ConnectionConfigError("ssh username not defined")
    try:
        password = c['password']
    except KeyError:
        raise ConnectionConfigError("ssh password not defined")
    try:
        port = int(c['port'])
    except KeyError:
        logging.debug("No ssh port specified - using default port 22")
        port = 22
    except ValueError:
        raise ConnectionConfigError(
            "invalid port value: %s"%(c['port']))
    try:
        cli = cliexpect.SshCLI(
            address, username, password, port, prompt=config['command']['prompt'],
            linesep=config['command']['linesep'],
            sendlinesep=config['command']['sendlinesep'],
            verbose=((50 - dctrl.logger.getEffectiveLevel()) / 20),
            verbose_prefix=args['run'].get_group_name(upper=True) + "> ",
            logfile=args.get('logfile', None))
    except Exception, e:
        print >> sys.stderr, "dctrl: ssh connection to %s@%s:%d failed: %s"%(
            username, address, port, e)
        return None

    cli.log("dctrl: opened ssh connection to %s@%s:%d"%(
            username, address, port))
    return cli

def connect_telnet_microcom():
    import dctrl.config
    config = dctrl.config.config
    cli = connect_telnet()
    try:
        cmd = config['command']['connection']['microcom']
    except:
        cmd = ""
    try:
        user = config['command']['connection']['username']
    except:
        user = root
    try:
        passw = config['command']['connection']['password']
    except:
        passw = root
    cli.sendline(user, noLogSend=True)
    cli.flush()
    cli.sendline(passw, noLogSend=True)
    cli.sendline(cmd, noLogSend=True)
    cli.flush()
    return cli

def connect_ssh_microcom():
    import dctrl.config
    config = dctrl.config.config
    cli = connect_ssh()
    try:
        cmd = config['command']['connection']['microcom']
    except:
        cmd = ""
    cli.sendline(cmd, noLogSend=True)
    cli.flush()
    return cli

_connection_types = {
    'serial' : connect_serial,
    'telnet' : connect_telnet,
    'ssh'    : connect_ssh,
    'telnet-microcom' : connect_telnet_microcom,
    'ssh-microcom' : connect_ssh_microcom,
}



