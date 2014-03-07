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

import os

class Repo(object):
    def __init__( self, xml, path ):
        self.path = path
        self.xml  = xml

        repoconfdir = os.path.join( path, "conf" )

        os.system( 'mkdir -p %s' % repoconfdir )

        repoconf = os.path.join( repoconfdir, "distributions" )
        fp = open(repoconf, "w")

        fp.write( "Origin: update XXX\n" )
        fp.write( "Label: update'\n" )
        fp.write( "Suite: " + xml.text("project/suite") + "\n" )
        fp.write( "Codename: " + xml.text("project/suite") + "\n" )
        fp.write( "Version: 7.0\n" )
        fp.write( "Architectures: " + xml.text("project/arch", key="arch" ) + "\n" )
        fp.write( "Components: main\n" )
        fp.write( "Description: Update Repository XXX\n" )

        fp.close()

    def includedeb( self, path ):
        os.system( "reprepro --basedir " + self.path + " includedeb " + self.xml.text("project/suite") + " " + path ) 
    
