# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import os

from mako.template import Template
from mako import exceptions

from elbepack.treeutils import etree
from elbepack.directories import mako_template_dir, default_preseed_fname


def fix_linebreak_escapes(s):
    return s.replace('\\\n', '${"\\\\"}\n')


def template(fname, d, linebreak=False):
    try:
        if linebreak:
            return Template(
                filename=fname,
                preprocessor=fix_linebreak_escapes).render(
                **d)

        return Template(filename=fname).render(**d)
    except BaseException:
        print(exceptions.text_error_template().render())
        raise


def write_template(outname, fname, d, linebreak=False):
    outfile = open(outname, 'w')
    outfile.write(template(fname, d, linebreak))
    outfile.close()


def write_pack_template(outname, fname, d, linebreak=False):
    template_name = os.path.join(mako_template_dir, fname)

    write_template(outname, template_name, d, linebreak)


def get_preseed(xml):
    def_xml = etree(default_preseed_fname)

    preseed = {}
    for c in def_xml.node('/preseed'):
        k = (c.et.attrib['owner'], c.et.attrib['key'])
        v = (c.et.attrib['type'], c.et.attrib['value'])

        preseed[k] = v

    if not xml.has('./project/preseed'):
        return preseed

    for c in xml.node('/project/preseed'):
        k = (c.et.attrib['owner'], c.et.attrib['key'])
        v = (c.et.attrib['type'], c.et.attrib['value'])

        preseed[k] = v

    return preseed


def get_initvm_preseed(xml):
    def_xml = etree(default_preseed_fname)

    preseed = {}
    for c in def_xml.node('/preseed'):
        k = (c.et.attrib['owner'], c.et.attrib['key'])
        v = (c.et.attrib['type'], c.et.attrib['value'])

        preseed[k] = v

    if not xml.has('./initvm/preseed'):
        return preseed

    for c in xml.node('/initvm/preseed'):
        k = (c.et.attrib['owner'], c.et.attrib['key'])
        v = (c.et.attrib['type'], c.et.attrib['value'])

        preseed[k] = v

    return preseed


def preseed_to_text(pres):
    retval = ''
    for k, v in pres.items():
        retval += f'{k[0]}\t{k[1]}\t{v[0]}\t{v[1]}\n'

    return retval
