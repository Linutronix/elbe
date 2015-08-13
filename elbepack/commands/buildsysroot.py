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


from optparse import OptionParser
import sys
import os

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog buildsysroot [options] <builddir>")
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    try:
        project = ElbeProject( args[0], override_buildtype=opt.buildtype,
                skip_validate=opt.skip_validation )
    except ValidationError as e:
        print str(e)
        print "xml validation failed. Bailing out"
        sys.exit(20)

    sysrootfilelist = os.path.join(project.builddir, "sysroot-filelist")

    with project.buildenv.rfs:
        project.log.do( "chroot %s /usr/bin/symlinks -cr /usr/lib" %
                project.chrootpath )

    triplet = project.xml.defs["triplet"]


    paths = [ './usr/include', './lib/*.so', './lib/*.so.*',
            './lib/' + triplet, './usr/lib/*.so', './usr/lib/*.so',
            './usr/lib/*.so.*', './usr/lib/' + triplet ]

    
    project.log.do( "rm %s" % sysrootfilelist, allow_fail=True)

    os.chdir( project.chrootpath )


    for p in paths:
        project.log.do( 'find -path "%s" >> %s' % (p, sysrootfilelist) )
    project.log.do( "tar cvfJ %s/sysroot.tar.xz -C %s -T %s" %
            (project.builddir, project.chrootpath, sysrootfilelist) )
    
    

