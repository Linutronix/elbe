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


from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import os

def create_zip_archive( zipfilename, path, inarchpath ):
    with ZipFile( zipfilename, "w", ZIP_DEFLATED ) as zf:
        for root, dirs, files in os.walk(path):
            archpath = os.path.join( inarchpath, os.path.relpath( root, path ) )
            zf.write( root, archpath )
            for f in files:
                filename = os.path.join( root, f )
                if not os.path.isfile(filename):
                    continue
                archname = os.path.join( archpath, f )
                # this hack is needed to avoid leading ./ in the archive
                while archname.startswith ('./'):
                    archname = archname[2:]
                zi = ZipInfo( archname)
                stat = os.stat( path + '/' + archname )
                zi.external_attr = stat.st_mode << 16L
                # this hack is needed to use the external attributes
                # there is no way to set a zipinfo object directly to an archive
                with open (filename, 'rb') as f:
                    zf.writestr( zi, f.read () )

