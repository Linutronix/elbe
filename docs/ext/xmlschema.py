# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import textwrap

from docutils import nodes

from sphinx.util.docutils import SphinxDirective

from elbepack.treeutils import elem, etree


ELEM = '{http://www.w3.org/2001/XMLSchema}element'
CPLX = '{http://www.w3.org/2001/XMLSchema}complexType'
DOC = '{http://www.w3.org/2001/XMLSchema}annotation/{http://www.w3.org/2001/XMLSchema}documentation'
ATTR = '{http://www.w3.org/2001/XMLSchema}attribute'
SEQ = '{http://www.w3.org/2001/XMLSchema}sequence'
SIMP = '{http://www.w3.org/2001/XMLSchema}simpleType'
GRP = '{http://www.w3.org/2001/XMLSchema}group'
RSTR = '{http://www.w3.org/2001/XMLSchema}restriction'
MAXI = '{http://www.w3.org/2001/XMLSchema}maxInclusive'
MINI = '{http://www.w3.org/2001/XMLSchema}minInclusive'


class XmlSchema(SphinxDirective):
    required_arguments = 1

    def run(self):
        rel, path = self.env.relfn2path(self.arguments[0])
        self.env.note_dependency(rel)
        self.env.note_dependency(__file__)

        xml = etree(path)

        return list(self.printschema(xml))

    def printschema(self, xml):
        for i, n in enumerate(xml.all('./')):
            yield from self.printnode(n)

    def printnode(self, n):
        if n.tag == ELEM:
            yield from self.do_element(n)
        elif n.tag == SIMP:
            yield from self.do_simple(n)
        elif n.tag == CPLX:
            yield from self.do_complex(n)
        elif n.tag == GRP:
            yield from self.do_group(n)

    @property
    def _srcline(self):
        return self.state_machine.abs_line_number()

    @staticmethod
    def docindent(node, indent=0):
        try:
            s = node.text('.//%s' % DOC)
        except Exception:
            return 'FIXME - I have no documentation'
        else:
            return textwrap.indent(textwrap.dedent(s), indent*' ').strip('\n')

    @staticmethod
    def element_example(n):
        name = n.et.attrib['name']
        _type = n.et.attrib['type']
        return '<%s> %s </%s>' % (name, _type, name)

    @staticmethod
    def genlink(typ):
        if typ.startswith('rfs:'):
            return '<<'+typ[4:]+','+typ+'>>'
        else:
            return typ

    @staticmethod
    def cardinality(e):
        min = None
        max = None

        retval = ''

        if e.et.attrib.has_key('minOccurs'):
            min = e.et.attrib['minOccurs']

        if e.et.attrib.has_key('maxOccurs'):
            min = e.et.attrib['maxOccurs']

        if min == '0':
            retval += '*optional* '

        if max == '1' and min == '1':
            retval += '*mandatory'

        return retval

    def doc(self, e):
        return self.docindent(e, 2)

    def element_doc(self, e):
        name = e.et.attrib['name']
        _type = e.et.attrib['type']
        return '%s %s %s::\n%s' % (name,
                                   self.genlink(_type),
                                   self.cardinality(e),
                                   self.doc(e))

    def attr_doc(self, a):
        if 'name' in a.et.attrib:
            return '[attr] %s' % self.element_doc(a)
        return ''

    def do_element(self, n):
        name = n.et.attrib['name']
        section = nodes.section(ids=[name])
        title = nodes.title(text=name + ' type: ')
        title += nodes.emphasis(text=n.et.attrib['type'])
        section += title
        section += nodes.paragraph(text=self.docindent(n))
        return [section]

    def highlight(self, source):
        node = nodes.literal_block(source, source)
        node['language'] = 'xml'
        return node

    def do_complex(self, n):
        name = n.et.attrib['name']
        section = nodes.section(ids=[name])
        title = nodes.title(text='TYPE: ' + name)
        section += title
        section += nodes.paragraph(text=self.docindent(n))

        example = nodes.section(ids=[name + '-example'])
        example += nodes.title(text='Example')
        example_source = '\n'.join([
            f'<{name}>',
            *['    ' + self.element_example(e) for e in n.all(f'.//{ELEM}')],
            *[
                self.element_example(elem(e))
                for ref in n.all(f'.//{GRP}')
                for g in ref.et.getroottree().findall(
                    './%s[@name="%s"]' % (GRP, ref.et.attrib['ref'].strip('rfs:')))
                for e in g.findall('.//%s' % ELEM)
            ],
            f'</{name}>',
        ])
        example += self.highlight(example_source)
        section += example

        elements = nodes.section(ids=[name + '-elements'])
        elements += nodes.title(text='Elements description')
        elements += [nodes.paragraph(text=self.attr_doc(a)) for a in n.all(f'.//{ATTR}')]
        elements += [nodes.paragraph(text=self.element_doc(a)) for a in n.all(f'.//{ELEM}')]

        section += elements
        return [section]

    def do_simple(self, n):
        name = n.et.attrib['name']
        section = nodes.section(ids=[name])
        section += nodes.title(text='SIMPLE TYPE: ' + name)
        section += nodes.paragraph(text=self.docindent(n))

        if n.has(RSTR):
            base_type = nodes.section(ids=[name + '-base-type'])
            base_type += nodes.title(text='Base Type')
            par = nodes.paragraph()
            par += nodes.emphasis(text=n.node(RSTR).et.attrib['base'])
            base_type += par
            section += base_type

            restrictions = nodes.section(ids=[name + '-restrictions'])
            restrictions += nodes.title(text='Restrictions')
            table = nodes.table()
            tgroup = nodes.tgroup()
            tgroup += [nodes.colspec(colwidth=1), nodes.colspec(colwidth=1)]
            tbody = nodes.tbody()
            for r in n.node(RSTR):
                row = nodes.row()
                col1 = nodes.entry()
                col1 += nodes.paragraph(
                        text=r.tag.removeprefix('{http://www.w3.org/2001/XMLSchema}'))
                col2 = nodes.entry()
                col2 += nodes.paragraph(text=r.et.attrib['value'])
                row += [col1, col2]
                tbody += row
            tgroup += tbody
            table += tgroup
            restrictions += table
            section += restrictions

        return [section]

    def do_group(self, n):
        name = n.et.attrib['name']
        section = nodes.section(ids=[name])
        title = nodes.title(text='GROUP : ' + name)
        section += title
        section += nodes.paragraph(text=self.docindent(n))

        yield section
        for r in [self.printnode(e) for e in n.all(f'.//{ELEM}')]:
            yield from r


def setup(app):
    app.add_directive('xmlschema', XmlSchema)

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
