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
    oparser = OptionParser(usage="usage: %prog chroot [options] <builddir> [cmd]")
    oparser.add_option( "--skip-validation", action="store_true",
                        dest="skip_validation", default=False,
                        help="Skip xml schema validation" )
    oparser.add_option( "--target", action="store_true", dest="target",
                        help="chroot into target instead of buildenv",
                        default=False )
    oparser.add_option( "--buildtype", dest="buildtype",
                        help="Override the buildtype" )

    (opt,args) = oparser.parse_args(argv)

    if len(args) < 1:
        print "wrong number of arguments"
        oparser.print_help()
        sys.exit(20)

    try:
        project = ElbeProject(args[0], override_buildtype=opt.buildtype,
                skip_validate=opt.skip_validation, skip_urlcheck=True)
    except ValidationError as e:
        print str(e)
        print "xml validation failed. Bailing out"
        sys.exit(20)

    os.environ["LANG"] = "C"
    os.environ["LANGUAGE"] = "C"
    os.environ["LC_ALL"] = "C"
    # TODO: howto set env in chroot?
    os.environ["PS1"] = project.xml.text ('project/name') + ': \w\$'

    cmd = "/bin/bash"

    if len(args) > 1:
        cmd = ""
        cmd2 = args[1:]
        for c in cmd2:
            cmd += (c + " ")

    if opt.target:
        with project.targetfs:
            os.system( "/usr/sbin/chroot %s %s" % (project.targetpath, cmd) )
    else:
        with project.buildenv.rfs:
            os.system( "/usr/sbin/chroot %s %s" % (project.chrootpath, cmd) )
