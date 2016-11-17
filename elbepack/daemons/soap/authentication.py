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



from faults import SoapElbeDBError, SoapElbeAuthenticationFailed, SoapElbeNotLoggedIn, SoapElbeNotAuthorized
from functools import wraps

def authenticated_uid(func):
    """ decorator, which Checks, that the current session is logged in,
        and also passes the current uid to the function

        Allows for being wrapped in a soapmethod...

        Example:
            @soapmethod (String, _returns=Array(SoapFile))
            @authenticated_uid
            def get_files (self, uid, builddir): 
    """
    if func.func_code.co_argcount == 2:
        @wraps(func)
        def wrapped(self):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid)
        return wrapped
    elif func.func_code.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid,arg1)
        return wrapped
    elif func.func_code.co_argcount == 4:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid,arg1,arg2)
        return wrapped
    elif func.func_code.co_argcount == 5:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid,arg1,arg2,arg3)
        return wrapped
    elif func.func_code.co_argcount == 6:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid,arg1,arg2,arg3,arg4)
        return wrapped
    elif func.func_code.co_argcount == 7:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self,uid,arg1,arg2,arg3,arg4,arg5)
        return wrapped
    else:
        raise Exception( "arg count %d not implemented" % func.func_code.co_argcount )




def authenticated_admin(func):
    """ decorator, which Checks, that the current session is logged in as an admin

        Allows for being wrapped in a soapmethod...

        Example:
            @soapmethod (String, _returns=Array(SoapFile))
            @authenticated_uid
            def get_files (self, uid, builddir): 
    """
    if func.func_code.co_argcount == 1:
        @wraps(func)
        def wrapped(self):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()
            return func(self)
        return wrapped
    elif func.func_code.co_argcount == 2:
        @wraps(func)
        def wrapped(self, arg1):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()

            return func(self,arg1)
        return wrapped
    elif func.func_code.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()
            return func(self,arg1,arg2)
        return wrapped
    else:
        raise Exception( "arg count %d not implemented" % func.func_code.co_argcount )
