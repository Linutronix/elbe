# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2014  Linutronix GmbH
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

# Please note that to get VALID (Trusted), the key that the file was signed
# with has to have ultimate trust level, otherwise you'll only get
# VALID (Untrusted)!

from __future__ import print_function

from elbepack.gpg import unsign_file

def run_command( argv ):
    if(len(argv) != 1):
        print("Wrong number of arguments.")
        print("Please pass the name of the file to unsign.")
        return

    fname = unsign_file( argv[0] )
    if fname:
        print("unsigned file: %s" % fname)
    else:
        print("removing signature failed")
