# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH
# SPDX-FileCopyrightText: 2015 Matthias Buehler <Matthias.Buehler@de.trumpf.com>

from optparse import OptionParser
import sys
import os
import logging

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.efilesystem import ChRootFilesystem
from elbepack.log import elbe_logging
from elbepack.rpcaptcache import get_rpcaptcache

from elbepack.cdroms import mk_source_cdrom, mk_binary_cdrom, CDROM_SIZE


def run_command(argv):

    # pylint disable=too-many-statements

    oparser = OptionParser(usage='usage: %prog mkcdrom [options] <builddir>')
    oparser.add_option('--skip-validation', action='store_true',
                       dest='skip_validation', default=False,
                       help='Skip xml schema validation')
    oparser.add_option('--buildtype', dest='buildtype',
                       help='Override the buildtype')
    oparser.add_option('--arch', dest='arch',
                       help='Override the architecture')
    oparser.add_option('--codename', dest='codename',
                       help='Override the codename')
    oparser.add_option('--init_codename', dest='init_codename',
                       help='Override the initvm codename')
    oparser.add_option('--rfs-only', action='store_true',
                       dest='rfs_only', default=False,
                       help='builddir points to RFS')
    oparser.add_option('--log', dest='log',
                       help='Log to filename')
    oparser.add_option('--binary', action='store_true',
                       dest='binary', default=False,
                       help='build binary cdrom')
    oparser.add_option('--source', action='store_true',
                       dest='source', default=False,
                       help='build source cdrom')
    oparser.add_option(
        '--cdrom-size',
        action='store',
        dest='cdrom_size',
        default=CDROM_SIZE,
        help='Source ISO CD size in bytes')

    (opt, args) = oparser.parse_args(argv)

    if len(args) != 1:
        print('wrong number of arguments', file=sys.stderr)
        oparser.print_help()
        sys.exit(74)

    with elbe_logging({'files': opt.log}):

        if not opt.rfs_only:
            try:
                project = ElbeProject(args[0],
                                      override_buildtype=opt.buildtype,
                                      skip_validate=opt.skip_validation)
            except ValidationError:
                logging.exception('XML validation failed.  Bailing out')
                sys.exit(75)

            builddir = project.builddir
            rfs = project.buildenv.rfs
            xml = project.xml
            arch = xml.text('project/arch', key='arch')
            codename = xml.text('project/suite')
            init_codename = xml.get_initvm_codename()
        else:
            builddir = os.path.abspath(os.path.curdir)
            rfs = ChRootFilesystem(args[0])
            arch = opt.arch
            codename = opt.codename
            init_codename = opt.init_codename
            xml = None

        generated_files = []
        if opt.source:
            with rfs:
                cache = get_rpcaptcache(rfs, arch)
                components = {'main': (rfs,
                                       cache,
                                       cache.get_corresponding_source_packages())}
                generated_files += mk_source_cdrom(components, codename,
                                                   init_codename, builddir,
                                                   opt.cdrom_size)

        if opt.binary:
            with rfs:
                generated_files += mk_binary_cdrom(rfs,
                                                   arch,
                                                   codename,
                                                   init_codename,
                                                   xml,
                                                   builddir)

        logging.info('Image Build finished.')
        logging.info('Files generated:\n%s',
                     '\n'.join([str(f) for f in generated_files]))
