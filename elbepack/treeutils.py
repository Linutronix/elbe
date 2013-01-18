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

from xml.etree.cElementTree import ElementTree, SubElement

# ElementTree helpers

class eiter(object):
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        return self

    def next(self):
        return elem(self.it.next())

class ebase(object):
    def text( self, path, **args ):
        el = self.et.find("./"+path)
        if (el is None) and not args.has_key("default"):
            return "no elem %s in %s" % (path, str(self))
        elif (el is None) and args.has_key("default"):
            return args["default"]
        else:
            return el.text

    @property
    def tag( self ):
        return self.et.tag

    def node( self, path ):
        retval = self.et.find("./"+path)
        if not retval is None:
            return elem( retval )
        else:
            return None

    def all( self, path ):
        return map(elem, self.et.findall(path))

    def __iter__( self ):
        return eiter(iter(self.et))

    def has( self, path ):
        return not (self.et.find(path) is None)

    def set_text( self, text ):
        self.et.text = text

    def clear( self ):
        self.et.clear()


class elem(ebase):
    def __init__( self, el ):
        ebase.__init__( self )
        self.et = el

    def ensure_child( self, tag ):
        retval = self.et.find("./"+tag)
        if not retval is None:
            return elem( retval )
        else:
            return elem( SubElement( self.et, tag ) )

    def append( self, tag ):
        retval = elem( SubElement( self.et, tag ) )
        retval.et.tail = '\n'
        return retval


    def clear( self ):
        self.et.clear()



class etree(ebase):
    def  __init__( self, fname ):
        ebase.__init__( self )
        self.et = ElementTree( file=fname )

    def write( self, fname ):
        self.et.write(fname)

    def ensure_child( self, tag ):
        retval = self.et.find("./"+tag)
        if not retval is None:
            return elem( retval )
        else:
            return elem( SubElement( self.et.getroot(), tag ) )

