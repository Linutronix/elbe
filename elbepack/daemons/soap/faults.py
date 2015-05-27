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

from soaplib.serializers.primitive import Fault

class SoapElbeDBError( Fault ):
    def __init__(self, dberr):
        Fault.__init__(self, faultcode="ElbeDBError", faultstring=str(dberr))

class SoapElbeAuthenticationFailed( Fault ):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeAuthenticationFailed", faultstring="Authentication Failed")

class SoapElbeNotLoggedIn( Fault ):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeNotLoggedIn", faultstring="Not authenticated ! Cant let you perform this command.")

class SoapElbeNotAuthorized( Fault ):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeNotAuthorized", faultstring="Not Authorized ! Cant let you perform this command.")

