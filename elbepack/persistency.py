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
#


max_objects = 3

from datetime import datetime

class Managed(object):
    cache = {}

    @classmethod
    def register(cls, obj):
        if len(cls.cache.keys()) >= max_objects:
            # LRU Logic here
            minimal = cls.cache.keys()[0]
            for i in cls.cache.keys():
                if cls.cache[i].lastaccess < cls.cache[minimal].lastaccess:
                    minimal = i
            del cls.cache[minimal]
        cls.cache[obj.path] = obj

    def is_registered(self):
        return hasattr(self,'path')

    def __new__(cls,path):
        if path in cls.cache:
            inst = cls.cache[path]
            inst.lastaccess = datetime.now()
        else:
            return object.__new__(cls)

    def __init__(self, path):
        if self.is_registered():
            return

        self.path = path
        self.lastaccess = datetime.now()
        self.register(self)


class Derived(Managed):

    def __init__(self,path):

        # Init is called, even if we are coming from the cache
        if self.is_registered():
            return

        Managed.__init__(self,path)

        print "real init"
        self.bla = "hello"

    def __del__(self):
        print "removing object ", self.path


