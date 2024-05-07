# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019 Linutronix GmbH

import logging

# https://wiki.osdev.org/ISO_9660
iso_options = {
    'sysid':     ('-sysid',      32, 'Specifies the system ID',              'strA'),
    'volid':     ('-V',          32, 'Specifies the volume ID',              'strD'),
    'volset':    ('-volset',    128, 'Specifies the volume set ID',          'strD'),
    'publisher': ('-publisher', 128, 'Specifies the publisher ID',           'strA'),
    'preparer':  ('-p',         128, 'Specifies the preparer ID',            'strA'),
    'app':       ('-A',         128, 'Specifies the application ID',         'strA'),
    'copyright': ('-copyright',  38, 'Specifies copyright filename on disc', 'strD'),
    'abstract':  ('-abstract',   36, 'Specifies the abstract filename',      'strD'),
    'biblio':    ('-biblio',     37, 'Specifies the bibliographic filename', 'strD'),
}

encoding = {
    'strA': """ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_!"%&'()*+,-./:;<=>? """,
    'strD': """ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"""
}


def iso_option_valid(opt_name, text):
    if opt_name not in iso_options:
        return False
    str_type = encoding[iso_options[opt_name][3]]
    if len(text) > iso_options[opt_name][1]:
        return len(text) - iso_options[opt_name][1]
    for c in text:
        if c not in str_type:
            return c
    return True


def get_iso_options(xml):
    options = []
    src_opts = xml.node('src-cdrom/src-opts')
    if src_opts is None:
        return options
    for node in src_opts:
        if node.tag not in iso_options:
            continue
        option = iso_options[node.tag]
        logging.info('Adding option %s\n%s', node.tag, option[2])
        text = node.et.text[:option[1]]
        options.append('%s "%s"' % (option[0], text.replace('"', '\\"')))
    return options
