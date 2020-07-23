# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# elbepack/commands/test.py - Elbe unit test wrapper

import enum
import optparse
import os
import re
import unittest
import warnings

import junit_xml as junit

class ElbeTestLevel(enum.IntEnum):
    BASE   = enum.auto()
    EXTEND = enum.auto()
    INITVM = enum.auto()
    FULL   = enum.auto()


class ElbeTestCase(unittest.TestCase):

    level = ElbeTestLevel.BASE

    def __init__(self, methodName='runTest', param=None):
        self.methodName = methodName
        self.param = param
        super().__init__(methodName)

    def __str__(self):
        name = super(ElbeTestCase, self).__str__()
        if self.param:
            return "%s : param=%s" % (name, self.param)
        return name

    def parameterize(self, param):
        return self.__class__(methodName=self.methodName, param=param)

# TODO:py3 - Remove useless object inheritance
# pylint: disable=useless-object-inheritance
class ElbeTestSuite(object):

    # This must be a list not a set!!!
    tests  = []

    def __init__(self, tests):

        for test in tests:

            if isinstance(test, ElbeTestSuite):
                continue

            if not hasattr(test, "params"):
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
        N       = int(N)

        elected = []

        rc = re.compile(regex, re.IGNORECASE)

        self.tests.sort(key=lambda x: str(x))

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

def run_command(argv):

    # pylint: disable=too-many-locals

    this_dir = os.path.dirname(os.path.realpath(__file__))
    top_dir  = os.path.join(this_dir, "..", "..")

    oparser = optparse.OptionParser(usage="usage: %prog [options]")

    oparser.add_option("-f", "--filter", dest="filter",
                       metavar="REGEX", type="string", default=".*",
                       help="Run specific test according to a filter rule")

    oparser.add_option("-l", "--level", dest="level",
                       type="string", default="BASE",
                       help="Set test level threshold")

    oparser.add_option("-i", "--invert", dest="invert_re",
                      action="store_true", default=False,
                      help="Invert the matching of --filter")

    oparser.add_option("-d", "--dry-run", dest="dry_run",
                       action="store_true", default=False,
                       help="List tests that would have been executed and exit")

    oparser.add_option("-p", "--parallel", dest="parallel",
                       type="string", default="0,1",
                       help="Run every thest where test_ID % N == node_ID")

    oparser.add_option("-o", "--output", dest="output",
                       type="string", default=None,
                       help="Write XML output to file")

    (opt, _) = oparser.parse_args(argv)

    # Set test level threshold
    if opt.level not in ElbeTestLevel.__members__:
        print("Invalid level value '%s'. Valid values are: %s" %
              (opt.level, ", ".join(key for key in ElbeTestLevel.__members__)))
        os.sys.exit(20)

    ElbeTestCase.level = ElbeTestLevel[opt.level]

    # Find all tests
    loader            = unittest.defaultTestLoader
    loader.suiteClass = ElbeTestSuite
    suite             = loader.discover(top_dir)

    # then filter them
    suite.filter_test(opt.parallel, opt.filter, opt.invert_re)

    # print them
    suite.ls()

    # Dry run? Just exit gently
    if opt.dry_run:
        print("This was a dry run. No tests were executed")
        os.sys.exit(0)

    cases = []

    err_cnt  = 0
    fail_cnt = 0

    for test in suite:

        result = unittest.TestResult()

        test.run(result)

        case = junit.TestCase(name=str(test))

        for error in result.errors:
            case.add_error_info(message=error[1])
            err_cnt += 1

        for failure in result.failures:
            case.add_failure_info(message=failure[1])
            fail_cnt += 1

        for skip in result.skipped:
            case.add_skipped_info(message=skip[1])

        cases.append(case)

    ts = junit.TestSuite(name="test", test_cases=cases)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = junit.TestSuite.to_xml_string([ts], encoding="utf-8")

    if opt.output is None:
        print(results)
    else:
        with open(opt.output, "w") as f:
            f.write(results)

    os.sys.exit(err_cnt | fail_cnt)
