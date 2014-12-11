#!/usr/bin/env python
#
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

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ValidationError
from elbepack.updatepkg import gen_update_pkg, MissingData

def run_command( argv ):
    oparser = OptionParser(usage="usage: %prog gen_update [options] <xmlfile>")
    oparser.add_option( "-t", "--target", dest="target",
                        help="directoryname of target" )
    oparser.add_option( "-o", "--output", dest="output",
                        help="filename of the update package" )
    oparser.add_option( "-n", "--name", dest="name",
                        help="name of the project (included in the report)" )
    oparser.add_option( "-p", "--pre-sh", dest="presh_file",
                        help="script that is executed before the update will be applied" )
    oparser.add_option( "-P", "--post-sh", dest="postsh_file",
                        help="script that is executed after the update was applied" )
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )
    oparser.add_option( "--debug", action="store_true", dest="debug",
                        default=False,
                        help="Enable various features to debug the build" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) != 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    if not opt.target:
        print "No target specified"
        sys.exit(20)

    if not opt.output:
        print "No output file specified"
        sys.exit(20)

    if opt.buildtype:
        buildtype = opt.buildtype
    else:
        buildtype = None

    try:
        project = ElbeProject( opt.target, name=opt.name,
                override_buildtype=buildtype,
                skip_validate=opt.skip_validation )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)

    if opt.presh_file:
        try:
            project.presh_file = open (opt.presh_file)
        except IOError as e:
            print 'pre.sh file invalid: %s' % str (e)
            sys.exit(20)

    if opt.postsh_file:
        try:
            project.postsh_file = open (opt.postsh_file)
        except IOError as e:
            print 'post.sh file invalid: %s' % str (e)
            sys.exit(20)

    try:
        gen_update_pkg( project, args[ 0 ], opt.output, buildtype,
                opt.skip_validation, opt.debug )
    except ValidationError:
        print "xml validation failed. Bailing out"
        sys.exit(20)
    except MissingData as e:
        print str(e)
        sys.exit(20)

    if project.postsh_file:
        project.postsh_file.close ()

    if project.presh_file:
        project.presh_file.close ()
