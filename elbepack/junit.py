# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import junit_xml as junit


class TestException(Exception):
    pass

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class TestSuite(object):

    test_dict = {}

    def __init__(self, node, target):
        super(TestSuite, self).__init__()
        self.node = node
        self.target = target

    @staticmethod
    def to_file(output, tss):
        with open(output, 'w') as f:
            junit.TestSuite.to_file(f, tss, prettyprint=True)

    @classmethod
    def register(cls, tag, register=True):
        def _register(test):
            test.tag = tag
            if register is True:
                cls.test_dict[tag] = test
            return test
        return _register

    def do_test(self, node, target):
        if node.tag not in self.test_dict:
            raise TestException("Invalid Test %s" % node.tag)
        test = self.test_dict[node.tag]
        return test(node, target)()

    def __call__(self):
        test_cases = []
        for test in self.node:
            try:
                test_cases.append(self.do_test(test, self.target))
            except TestException:
                pass # TODO - Handle me!
        ts = junit.TestSuite(name=self.node.et.attrib["name"],
                             test_cases=test_cases)
        return ts

# TODO:py3 - Remove object inheritance
# pylint: disable=useless-object-inheritance
@TestSuite.register("BaseTest", register=False)
class BaseTest(object):

    tag = None

    def __init__(self, node, target):
        super(BaseTest, self).__init__()
        self.node = node
        self.target = target

    def __call__(self):
        raise TestException("Unimplemented Test %s" % self.tag)


@TestSuite.register("file-exists")
class TestFileExists(BaseTest):

    def __call__(self):
        path = self.node.et.text
        test = junit.TestCase(name=path, classname=self.tag)
        if not self.target.exists(path):
            test.add_failure_info(message="FAILED")
        return test
