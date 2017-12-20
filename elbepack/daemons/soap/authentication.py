# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from faults import SoapElbeNotLoggedIn, SoapElbeNotAuthorized
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
    elif func.__code__.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1)
        return wrapped
    elif func.__code__.co_argcount == 4:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2)
        return wrapped
    elif func.__code__.co_argcount == 5:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3)
        return wrapped
    elif func.__code__.co_argcount == 6:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3, arg4)
        return wrapped
    elif func.__code__.co_argcount == 7:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5):
            s = self.transport.req_env['beaker.session']
            try:
                uid = s['userid']
            except KeyError:
                raise SoapElbeNotLoggedIn()

            return func(self, uid, arg1, arg2, arg3, arg4, arg5)
        return wrapped
    else:
        raise Exception(
            "arg count %d not implemented" %
            func.__code__.co_argcount)


def authenticated_admin(func):
    """ decorator, which Checks, that the current session is logged in as an admin

        Allows for being wrapped in a soapmethod...

        Example:
            @soapmethod (String, _returns=Array(SoapFile))
            @authenticated_uid
            def get_files (self, uid, builddir):
    """
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
    elif func.__code__.co_argcount == 2:
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
    elif func.__code__.co_argcount == 3:
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
    else:
        raise Exception(
            "arg count %d not implemented" %
            func.__code__.co_argcount)
