# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

from lxml.etree import ElementTree, SubElement, Element
from lxml.etree import XMLParser, parse
import copy

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
            if type(default) == str:
                return default
            else:
                return default[args["key"]]
        else:
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
        return not (self.et.find(path) is None)

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
        else:
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
        else:
            return elem(SubElement(self.et.getroot(), tag))

    def set_child_position(self, child, pos):
        root = self.et.getroot()
        root.remove(child.et)
        root.insert(pos, child.et)

    def setroot(self, tag):
        retval = elem(Element(tag))
        self.et._setroot(retval.et)
        return retval

    @property
    def root(self):
        return elem(self.et.getroot())
