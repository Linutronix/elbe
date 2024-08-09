# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import argparse
import logging
import os
import subprocess
import sys

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError, ValidationMode
from elbepack.log import elbe_logging


def run_command(argv):
    aparser = argparse.ArgumentParser(prog='elbe chroot')
    aparser.add_argument('--skip-validation', action='store_true',
                         dest='skip_validation', default=False,
                         help='Skip xml schema validation')
    aparser.add_argument('--target', action='store_true', dest='target',
                         help='chroot into target instead of buildenv',
                         default=False)
    aparser.add_argument('--buildtype', dest='buildtype',
                         help='Override the buildtype')
    aparser.add_argument('builddir')
    aparser.add_argument('cmd', nargs='*')

    args = aparser.parse_args(argv)

    with elbe_logging(streams=sys.stdout):
        try:
            project = ElbeProject(args.builddir,
                                  override_buildtype=args.buildtype,
                                  skip_validate=args.skip_validation,
                                  url_validation=ValidationMode.NO_CHECK)
        except ValidationError:
            logging.exception('XML validation failed.  Bailing out')
            sys.exit(73)

        os.environ['LANG'] = 'C'
        os.environ['LANGUAGE'] = 'C'
        os.environ['LC_ALL'] = 'C'
        # TODO: howto set env in chroot?
        os.environ['PS1'] = project.xml.text('project/name') + r': \w\$'

        chroot_args = args.cmd or ['/bin/bash']

        chroot, path = (project.targetfs, project.targetpath) if args.target else \
                       (project.buildenv, project.chrootpath)

        try:
            with chroot:
                subprocess.run([
                    '/usr/sbin/chroot', path,
                    *chroot_args,
                ], check=True)
        except subprocess.CalledProcessError as e:
            print(repr(e))
