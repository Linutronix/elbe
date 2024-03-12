# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import logging
import os
import subprocess
import sys
from optparse import OptionParser

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.log import elbe_logging


def run_command(argv):
    oparser = OptionParser(
        usage='usage: %prog chroot [options] <builddir> [cmd]')
    oparser.add_option('--skip-validation', action='store_true',
                       dest='skip_validation', default=False,
                       help='Skip xml schema validation')
    oparser.add_option('--target', action='store_true', dest='target',
                       help='chroot into target instead of buildenv',
                       default=False)
    oparser.add_option('--buildtype', dest='buildtype',
                       help='Override the buildtype')

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print('wrong number of arguments')
        oparser.print_help()
        sys.exit(72)

    with elbe_logging({'streams': sys.stdout}):
        try:
            project = ElbeProject(args[0],
                                  override_buildtype=opt.buildtype,
                                  skip_validate=opt.skip_validation,
                                  url_validation=ValidationMode.NO_CHECK)
        except ValidationError:
            logging.exception('XML validation failed.  Bailing out')
            sys.exit(73)

        os.environ['LANG'] = 'C'
        os.environ['LANGUAGE'] = 'C'
        os.environ['LC_ALL'] = 'C'
        # TODO: howto set env in chroot?
        os.environ['PS1'] = project.xml.text('project/name') + r': \w\$'

        chroot_args = ['/bin/bash']

        if len(args) > 1:
            chroot_args = args[1:]

        chroot, path = (project.targetfs, project.targetpath) if opt.target else \
                       (project.buildenv, project.chrootpath)

        try:
            with chroot:
                subprocess.run([
                    '/usr/sbin/chroot', path,
                    *chroot_args,
                ], check=True)
        except subprocess.CalledProcessError as e:
            print(repr(e))
