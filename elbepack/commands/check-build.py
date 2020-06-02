# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import optparse
import os
import tempfile
import traceback

from elbepack.log import elbe_logging
from elbepack.treeutils import etree
from elbepack.shellhelper import get_command_out, command_out, do, CommandError
from elbepack.filesystem import TmpdirFilesystem

DEVNULL = open(os.devnull, "w")

def run_command(argv):

    oparser = optparse.OptionParser(usage="usage: %prog check-build <cmd> <build-dir>")

    (_, args) = oparser.parse_args(argv)

    if len(args) < 2:
        oparser.print_help()
        os.sys.exit(20)

    if args[0] == "all":
        tests = [CheckBase.tests[tag] for tag in CheckBase.tests]
    elif args[0] in CheckBase.tests:
        tests = [CheckBase.tests[args[0]]]
    else:
        print("Invalid check test %s" % args[0])
        print("Valid tests are:\n\tall")
        for tag in CheckBase.tests:
            print("\t%s" % tag)
        os.sys.exit(20)

    total_cnt = 0
    fail_cnt  = 0

    with elbe_logging({"streams":None}):

        for test in tests:

            logging.info("Starting test %s (%s)", test.__name__, test.__doc__)
            os.chdir(args[1])
            ret = test()()

            total_cnt += 1
            if ret:
                fail_cnt += 1
                logging.error("FAILED test %s (%s)", test.__name__, test.__doc__)

        logging.info("Passed %d tests ouf of %d",
                     total_cnt - fail_cnt, total_cnt)

    os.sys.exit(fail_cnt)

class CheckException(Exception):
    pass

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class CheckBase(object):

    tests = dict()

    def __init__(self):
        self.ret = 0

    def __call__(self):
        try:
            self.ret = self.run()
        except CheckException as E:
            logging.exception(E)
            self.ret = 1
        except: # pylint: disable=bare-except
            logging.error(traceback.format_exc())
            self.ret = 1
        return self.ret

    @classmethod
    def register(cls, tag):
        def _register(test):
            cls.tests[tag] = test
            return test
        return _register

    # pylint: disable=no-self-use
    def run(self):
        raise Exception("Check run method not implemented")

    def fail(self, reason):
        raise CheckException(reason)
