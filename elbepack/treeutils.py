# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import print_function

import copy

from lxml.etree import ElementTree, SubElement, Element
from lxml.etree import XMLParser, parse

# ElementTree helpers

class eiter(object):
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            n = next(self.it)
            # A Comment has a callable tag
            # A better way for this predicate would be nice
            if not callable(n.tag):
                break

        return elem(n)

    def next(self):
        return self.__next__()


class ebase(object):
    def __init__(self, et):
        self.et = et

    def text(self, path, **args):
        el = self.et.find("./" + path)
        if (el is None) and "default" not in args:
            raise Exception("Cant find path %s" % path)
        elif (el is None) and "default" in args:
            default = args["default"]
            if isinstance(default, str):
                return default

            return default[args["key"]]

        return el.text

    @property
    def tag(self):
        return self.et.tag

    def node(self, path):
        retval = self.et.find("./" + path)
        if retval is not None:
            return elem(retval)
        else:
            return None

    def all(self, path):
        return map(elem, self.et.findall(path))

    def __iter__(self):
        return eiter(iter(self.et))

    def has(self, path):
        return not self.et.find(path) is None

    def set_text(self, text):
        self.et.text = text

    def clear(self):
        self.et.clear()

    def append_treecopy(self, other):
        self.et.append(copy.deepcopy(other.et))


class elem(ebase):
    def __init__(self, el):
        ebase.__init__(self, el)

    def ensure_child(self, tag):
        retval = self.et.find("./" + tag)
        if retval is not None:
            return elem(retval)

        return elem(SubElement(self.et, tag))

    def append(self, tag):
        retval = elem(SubElement(self.et, tag))
        retval.et.tail = '\n'
        return retval

    def set_child_position(self, child, pos):
        self.et.remove(child.et)
        self.et.insert(pos, child.et)

    def remove_child(self, child):
        self.et.remove(child.et)

    def bool_attr(self, attrname):
        attr = self.et.attrib.get(attrname)
        if attr is None:
            return False
        elif attr in ['true', '1']:
            return True
        elif attr in ['false', '0']:
            return False


class etree(ebase):
    def __init__(self, fname):
        if fname is not None:
            parser = XMLParser(huge_tree=True, remove_comments=False)
            et = parse(fname, parser=parser)
        else:
            et = ElementTree(file=None)

        ebase.__init__(self, et)

    def write(self, fname, encoding=None):
        # Make sure, that we end with a newline
        self.et.getroot().tail = '\n'
        self.et.write(fname, encoding=encoding)

    def tostring(self):
        return self.et.tostring()

    def ensure_child(self, tag):
        retval = self.et.find("./" + tag)
        if retval is not None:
            return elem(retval)

        return elem(SubElement(self.et.getroot(), tag))

    def set_child_position(self, child, pos):
        root = self.et.getroot()
        root.remove(child.et)
        root.insert(pos, child.et)

    def setroot(self, tag):
        retval = elem(Element(tag))
        self.et._setroot(retval.et)
        return retval

    def check_boolean(self, node, attributename):
        attr = node.get(attributename)
        if attr is None:
            return False
        elif attr in ['true', '1']:
            return True
        elif attr in ['false', '0']:
            return False

    @property
    def root(self):
        return elem(self.et.getroot())
