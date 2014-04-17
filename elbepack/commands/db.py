#!/usr/bin/env python
#
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


from elbepack.dbaction import DbAction

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def run_command (argv):

    if not len(argv):
        print 'elbe db - no action given'
        DbAction.print_actions ()
        return

    try:
        DbAction (argv[0]).execute (argv[1:])
    except KeyError:
        print 'elbe db - unknown action given'
        DbAction.print_actions ()
        return

    return
