# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from spyne.model.fault import Fault
from traceback import format_exc

from functools import wraps

# Import the Errors we try to catch wirh the
# soap_faults decorator
from elbepack.projectmanager import ProjectManagerError, InvalidState
from elbepack.elbexml import ValidationError
from elbepack.db import ElbeDBError, InvalidLogin


class SoapElbeDBError(Fault):
    def __init__(self, dberr):
        Fault.__init__(self, faultcode="ElbeDBError", faultstring=str(dberr))


class SoapElbeProjectError(Fault):
    def __init__(self, err):
        Fault.__init__(
            self,
            faultcode="ElbeProjectError",
            faultstring=str(err))


class SoapElbeAuthenticationFailed(Fault):
    def __init__(self):
        Fault.__init__(
            self,
            faultcode="ElbeAuthenticationFailed",
            faultstring="Authentication Failed")


class SoapElbeNotLoggedIn(Fault):
    def __init__(self):
        Fault.__init__(
            self,
            faultcode="ElbeNotLoggedIn",
            faultstring="Not authenticated ! "
                        "Cant let you perform this command.")


class SoapElbeNotAuthorized(Fault):
    def __init__(self):
        Fault.__init__(
            self,
            faultcode="ElbeNotAuthorized",
            faultstring="Not Authorized ! Cant let you perform this command.")


class SoapElbeValidationError(Fault):
    def __init__(self, exc):
        Fault.__init__(
            self,
            faultcode="ElbeValidationError",
            faultstring=exc.__repr__())


class SoapElbeInvalidState(Fault):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeInvalidState",
                       faultstring="Project is Busy ! Operation Invalid")


def soap_faults(func):
    """ decorator, which wraps Exceptions to the proper
        Soap Faults, and raises these.
    """
    if func.__code__.co_argcount == 1:
        @wraps(func)
        def wrapped(self):
            try:
                return func(self)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 2:
        @wraps(func)
        def wrapped(self, arg1):
            try:
                return func(self, arg1)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 3:
        @wraps(func)
        def wrapped(self, arg1, arg2):
            try:
                return func(self, arg1, arg2)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 4:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3):
            try:
                return func(self, arg1, arg2, arg3)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 5:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4):
            try:
                return func(self, arg1, arg2, arg3, arg4)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 6:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5):
            try:
                return func(self, arg1, arg2, arg3, arg4, arg5)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    if func.__code__.co_argcount == 7:
        @wraps(func)
        def wrapped(self, arg1, arg2, arg3, arg4, arg5, arg6):
            try:
                return func(self, arg1, arg2, arg3, arg4, arg5, arg6)
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except InvalidState as e:
                raise SoapElbeInvalidState()
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: " + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception as e:
                raise SoapElbeProjectError(format_exc())
        return wrapped
    else:
        raise Exception(
            "arg count %d not implemented" %
            func.__code__.co_argcount)
