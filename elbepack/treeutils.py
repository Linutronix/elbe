# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2017 Linutronix GmbH

import copy

from lxml.etree import Element, ElementTree, SubElement
from lxml.etree import Resolver, XMLParser, XMLSchema, parse, tostring

from elbepack.schema import xml_schema_file

# ElementTree helpers


def xml_bool(value):
    if value is None:
        return None
    if value in ('true', '1'):
        return True
    if value in ('false', '0'):
        return False
    raise ValueError(value)


class _ElbepackSchemaResolver(Resolver):
    def resolve(self, url, id, context):
        if url == 'http://www.w3.org/2009/01/xml.xsd':
            return self.resolve_file(xml_schema_file('xml.xsd'), context)


def dbsfed_schema():
    parser = XMLParser(no_network=True)
    parser.resolvers.add(_ElbepackSchemaResolver())
    with xml_schema_file('dbsfed.xsd') as schema_file:
        schema_tree = parse(schema_file, parser=parser)
    return XMLSchema(schema_tree)


class eiter:
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


class ebase:
    def __init__(self, et):
        self.et = et

    def text(self, path, **kwargs):
        el = self.et.find('./' + path)
        if el is None:
            if 'default' in kwargs:
                default = kwargs['default']
                if hasattr(default, '__getitem__') and 'key' in kwargs:
                    return default[kwargs['key']]
                return default

            raise Exception(f'Cant find path {path}')

        return el.text or ''

    @property
    def tag(self):
        return self.et.tag

    def node(self, path):
        retval = self.et.find('./' + path)
        if retval is not None:
            return elem(retval)
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

    def tostring(self):
        return tostring(self.et, encoding=str).strip()


class elem(ebase):

    def ensure_child(self, tag):
        retval = self.et.find('./' + tag)
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
        return xml_bool(self.et.attrib.get(attrname))

    def get_parent(self):
        return elem(self.et.getparent())


class etree(ebase):
    def __init__(self, fname):
        if fname is not None:
            parser = XMLParser(huge_tree=True, remove_comments=False)
            et = parse(fname, parser=parser)
        else:
            et = ElementTree(file=None)

        super().__init__(et)

    def write(self, fname, encoding=None):
        # Make sure, that we end with a newline
        self.et.getroot().tail = '\n'
        self.et.write(fname, encoding=encoding)

    def ensure_child(self, tag):
        retval = self.et.find('./' + tag)
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

    @property
    def root(self):
        return elem(self.et.getroot())
