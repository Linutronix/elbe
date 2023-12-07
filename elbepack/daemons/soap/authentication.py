# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2015-2018 Linutronix GmbH

from functools import wraps

from .faults import SoapElbeNotLoggedIn, SoapElbeNotAuthorized


def authenticated_uid(func):
    """ decorator, which Checks, that the current session is logged in,
        and also passes the current uid to the function

        Allows for being wrapped in a soapmethod...

        Example:
            @soapmethod (String, _returns=Array(SoapFile))
            @authenticated_uid
            def get_files (self, uid, builddir):
    """

    # Do not edit this code.  Although using *args is tempting here,
    # it will not work because Spyne is doing introspection on the
    # function's signature.  I think it would be possible to do
    # something with func.__code__.replace, but this requires deep
    # Python's internal knowledges.

    if func.__code__.co_argcount == 2:
        @wraps(func)
        def wrapped(self):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid)
        return wrapped
    if func.__code__.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1)
        return wrapped
    if func.__code__.co_argcount == 4:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2)
        return wrapped
    if func.__code__.co_argcount == 5:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3)
        return wrapped
    if func.__code__.co_argcount == 6:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3, arg4)
        return wrapped
    if func.__code__.co_argcount == 7:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3, arg4, arg5)
        return wrapped

    raise Exception(f'arg count {func.__code__.co_argcount} not implemented')


def authenticated_admin(func):
    """ decorator, which Checks, that the current session is logged in as an admin

        Allows for being wrapped in a soapmethod...

        Example:
            @soapmethod (String, _returns=Array(SoapFile))
            @authenticated_uid
            def get_files (self, uid, builddir):
    """

    # Do not edit this code.  Although using *args is tempting here,
    # it will not work because Spyne is doing introspection on the
    # function's signature.  I think it would be possible to do
    # something with func.__code__.replace, but this requires deep
    # Python's internal knowledges.

    if func.__code__.co_argcount == 1:
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
    if func.__code__.co_argcount == 2:
        @wraps(func)
        def wrapped(self, arg1):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()

            return func(self, arg1)
        return wrapped
    if func.__code__.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()
            return func(self, arg1, arg2)
        return wrapped
    if func.__code__.co_argcount == 6:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            if not self.app.pm.db.is_admin(uid):
                raise SoapElbeNotAuthorized()
            return func(self, arg1, arg2, arg3, arg4, arg5)
        return wrapped

    raise Exception(f'arg count {func.__code__.co_argcount} not implemented')
