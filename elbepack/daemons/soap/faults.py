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

from traceback import format_exc
from functools import wraps

from spyne.model.fault import Fault

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
        Fault.__init__(self, faultcode="ElbeProjectError",
                       faultstring=str(err))


class SoapElbeAuthenticationFailed(Fault):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeAuthenticationFailed",
                       faultstring="Authentication Failed")


class SoapElbeNotLoggedIn(Fault):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeNotLoggedIn",
                       faultstring="Not authenticated ! Can't let you perform this command.")


class SoapElbeNotAuthorized(Fault):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeNotAuthorized",
                       faultstring="Not Authorized ! Can't let you perform this command.")


class SoapElbeValidationError(Fault):
    def __init__(self, exc):
        Fault.__init__(self, faultcode="ElbeValidationError",
                       faultstring=exc.__repr__())


class SoapElbeInvalidState(Fault):
    def __init__(self):
        Fault.__init__(self, faultcode="ElbeInvalidState",
                       faultstring="Project is Busy ! Operation Invalid")


def soap_faults(func):
    """ decorator, which wraps Exceptions to the proper
        Soap Faults, and raises these.
    """
    if func.func_code.co_argcount <= 7:
        @wraps(func)
        def wrapped(self, *args):
            try:
                return func(self, *args)
            except InvalidState:
                raise SoapElbeInvalidState()
            except ProjectManagerError as e:
                raise SoapElbeProjectError(str(e))
            except ElbeDBError as e:
                raise SoapElbeDBError(str(e))
            except OSError as e:
                raise SoapElbeProjectError("OSError: %s" + str(e))
            except ValidationError as e:
                raise SoapElbeValidationError(e)
            except InvalidLogin:
                raise SoapElbeNotAuthorized()
            except Exception:
                raise SoapElbeProjectError(format_exc())
        return wrapped

    raise RuntimeError("arg count %d not implemented" % func.func_code.co_argcount)
