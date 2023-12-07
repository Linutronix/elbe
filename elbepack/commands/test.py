# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

# elbepack/commands/test.py - Elbe unit test wrapper

import enum
import io
import optparse
import os
import re
import unittest
import warnings

from elbepack.shellhelper import command_out

import junitxml as junit


class ElbeTestLevel(enum.IntEnum):
    BASE = enum.auto()
    EXTEND = enum.auto()
    INITVM = enum.auto()
    FULL = enum.auto()


class ElbeTestException(Exception):

    def __init__(self, cmd, ret, out):
        super().__init__()
        self.cmd = cmd
        self.ret = ret
        self.out = out

    def __repr__(self):
        return f'ElbeTestException: \"{self.cmd}\" returns {self.ret}'

    def __str__(self):
        return f'ElbeTestException: \"{self.cmd}\" returns {self.ret}'


def system(cmd, allow_fail=False):
    ret, out = command_out(cmd)
    if ret != 0 and not allow_fail:
        raise ElbeTestException(cmd, ret, out)


class ElbeTestCase(unittest.TestCase):

    level = ElbeTestLevel.BASE

    def __init__(self, methodName='runTest', param=None):
        self.methodName = methodName
        self.param = param
        self.stdout = None
        super().__init__(methodName)

    def __str__(self):
        name = super(ElbeTestCase, self).__str__()
        if self.param:
            return f'{name} : param={self.param}'
        return name

    def parameterize(self, param):
        return self.__class__(methodName=self.methodName, param=param)


class ElbeTestSuite:

    # This must be a list not a set!!!
    tests = []

    def __init__(self, tests):

        for test in tests:

            if isinstance(test, ElbeTestSuite):
                continue

            if not hasattr(test, 'params'):
                self.tests.append(test)
                continue

            if callable(test.params):
                params = test.params()
            else:
                params = test.params

            for param in params:
                self.tests.append(test.parameterize(param))

    def __iter__(self):
        for test in self.tests:
            yield test

    def filter_test(self, parallel, regex, invert):

        node_id, N = parallel.split(',')

        node_id = int(node_id)
        N = int(N)

        elected = []

        rc = re.compile(regex, re.IGNORECASE)

        self.tests.sort(key=str)

        # Tests filtered here are skipped quietly
        i = 0
        for test in self.tests:

            skip = False

            if i % N != node_id:
                skip = True

            if not skip and ((rc.search(str(test)) is None) ^ invert):
                skip = True

            if not skip:
                elected.append(test)

            i += 1

        self.tests = elected

    def ls(self):
        for test in self:
            print(test)


class ElbeTestResult(unittest.TestResult):

    def __init__(self):
        super().__init__()
        self.buffer = io.StringIO()
        self.result = junit.JUnitXmlResult(self.buffer)
        self.success = False

    def run_testsuite(self, suite):
        self.result.startTestRun()
        unittest.TestSuite(suite).run(self.result)
        self.result.stopTestRun()
        self.success = self.result.wasSuccessful()

    def wasSuccessful(self):
        return self.success

    def get_xml(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            results = self.buffer.getvalue()

        return results


def run_command(argv):

    this_dir = os.path.dirname(os.path.realpath(__file__))
    top_dir = os.path.join(this_dir, '..', '..')

    oparser = optparse.OptionParser(usage='usage: %prog [options]')

    oparser.add_option('-f', '--filter', dest='filter',
                       metavar='REGEX', type='string', default='.*',
                       help='Run specific test according to a filter rule')

    oparser.add_option('-l', '--level', dest='level',
                       type='string', default='BASE',
                       help='Set test level threshold')

    oparser.add_option('-i', '--invert', dest='invert_re',
                       action='store_true', default=False,
                       help='Invert the matching of --filter')

    oparser.add_option('-d', '--dry-run', dest='dry_run',
                       action='store_true', default=False,
                       help='List tests that would have been executed and exit')

    oparser.add_option('-p', '--parallel', dest='parallel',
                       type='string', default='0,1',
                       help='Run every thest where test_ID % N == node_ID')

    oparser.add_option('-o', '--output', dest='output',
                       type='string', default=None,
                       help='Write XML output to file')

    (opt, _) = oparser.parse_args(argv)

    # Set test level threshold
    if opt.level not in ElbeTestLevel.__members__:
        print(
            f"Invalid level value '{opt.level}'. Valid values are: "
            f"{', '.join(key for key in ElbeTestLevel.__members__)}")
        os.sys.exit(76)

    ElbeTestCase.level = ElbeTestLevel[opt.level]

    # Find all tests
    loader = unittest.defaultTestLoader
    loader.suiteClass = ElbeTestSuite
    suite = loader.discover(top_dir)

    # then filter them
    suite.filter_test(opt.parallel, opt.filter, opt.invert_re)

    # Dry run? Just exit gently
    if opt.dry_run:
        suite.ls()
        print('======================================================================\n'
              'This was a dry run. No tests were executed')
        os.sys.exit(0)

    result = ElbeTestResult()

    result.run_testsuite(suite)

    if opt.output is None:
        print(result.get_xml())
    else:
        with open(opt.output, 'w') as f:
            f.write(result.get_xml())

    if not result.wasSuccessful():
        print('Testsuite failed.')
        os.sys.exit(77)
