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

import json

unittest = __import__('unittest', level=0)
import logging
import copy

import os
import dctrl
import dctrl.command
from dtest.dtestcase import DtestTestCase
import dtest.testsetup

logger = logging.getLogger("dctrl")

class DctrlError(Exception):
    pass


class DctrlWrapper(DtestTestCase):

    def __init__(self, group, command, parent, params, testargs={}):
        self.testsetup = dtest.testsetup.testsetup()
        if hasattr(self.testsetup, 'DctrlConfigs'):
            self.dctrlconfigs = self.testsetup.DctrlConfigs

        self.variables = {}
        if hasattr(self.testsetup, 'Variables'):
            self.variables = self.testsetup.Variables

        cmd = dctrl.get_command(group, command)
        assert isinstance(cmd, dctrl.command.DctrlCommand)
        self.cmd = cmd
        self.parent = parent

        # Get default values for parameters having a default value
        self.params = copy.copy(cmd.parser.defaults)

        if hasattr(self.testsetup, 'DctrlCmdDefs'):
            for param in self.params:
                # First try overriding with entry DEFAULT which is cmd-unspecific
                try:
                    self.params[param] = self.testsetup.DctrlCmdDefs[param]['DEFAULT']
                except:
                    None

                # Try overriding with cmd-specific value
                try:
                    self.params[param] = self.testsetup.DctrlCmdDefs[param][cmd.name]
                except:
                    None

        # Override with parameters specified in yaml files
        self.params.update(params)

        self.testargs=testargs
        # when dtest is calling dctrl, we want to log
        # to the dtest logger. Dctrl modules should use
        # the dctrl logger not the root logger
        dctrl.logger = logging.getLogger('dtest')
        logger.debug("Creating DctrlWrapper Object. params: %s",self.params)
        super(DctrlWrapper, self).__init__('runTest')

    def __str__(self):
        s = '%s.%s.%s'%(self.parent, self.cmd.get_group_name(),
                        self.cmd.get_cmd_name())
        params = dict((key, value) for key, value in self.params.iteritems()
                      if key not in ('run',))
        if params:
            s += ' ' + str(params)
        return s

    @classmethod
    def setUpClass(cls):
        return

    def parseParams(self):
        self.variables['TMPDIR'] = self.tmpDir
        self.variables['TOPDIR'] = os.getcwd()
        for key, key_value in self.params.iteritems():
            if key_value is not None and isinstance(key_value,str):
                for var, var_val in self.variables.iteritems():
                    key_value=key_value.replace("_#_"+var+"_#_", var_val)
                self.params[key] = key_value

    def setUp(self):
        import dctrl.config
        cfg_idx = 0
        if 'cfg_idx' in self.testargs:
            cfg_idx = self.testargs['cfg_idx']
        if hasattr(self,'dctrlconfigs'):
            dctrlconfig = self.dctrlconfigs[cfg_idx]
        else:
            dctrlconfig = 'conf/dctrl.cfg'
        dctrl.config.load(dctrlconfig, self.cmd)
        self.parseParams()
        dctrl.config.config['params'] = self.params
        self.params['run'] = self.cmd
        #always log to file for dtest
        self.params['logfile'] = os.path.join(self.tmpDir, "output.log")
        logger.info("DctrlWrapper:setup(): saving dctrl cmd output to file: %s",self.params['logfile'])
        self.cmd.tmpDir = self.tmpDir

    def _runTest(self):
        logger.debug("DctrlWrapper: runTest(): running cmd: %s",self.cmd)
        ret = dctrl.command.run(self.cmd)
	data = ret[1]
        if type(data) == dict:
            data = json.dumps(data)
        if not ret[0] in (0,1,2):
            raise DctrlError('invalid return value: %r'%(repr(ret)))
        if len(data):
            self.output = data.rstrip()
        if ret[0] == 2:
            raise DctrlError(data)
        self.assertEqual(ret[0], 0, msg= 'dctrl command failed: ' + str(data))

    def fullDescription(self):
        if hasattr(self.cmd,"fullDescription"):
            # Use the fullDescription if possible
            return self.cmd.fullDescription()
        # Fallback to the shortDescription if there is no fullDescription
        return self.shortDescription()

    def shortDescription(self):
        """ Fetch the description from the test object Class
        with out this function the doc string of "runTest" would have been
        used. Doc string of runTest is currently empty so the descript would be
        None
        """
        if hasattr(self.cmd,"shortDescription"):
            # Use the shortDescript if possible
            return self.cmd.shortDescription()
        else:
            # Else just use the doc string
            return self.cmd.__doc__

    def runTest(self):
        self._runTest()


class DctrlWrapperExpectFail(DctrlWrapper):
    """ Like DctrlWrapper but decorates with expect failure"""

    def __init__(self, group, command, parent, params, testargs={}):
        super(DctrlWrapperExpectFail, self).__init__(
                group, command, parent, params, testargs)

    @unittest.expectedFailure
    def runTest(self):
        self._runTest()
