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

from xml.etree.cElementTree import ElementTree, SubElement, Element
import copy

# ElementTree helpers

class eiter(object):
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        return self

    def next(self):
        return elem(self.it.next())

class ebase(object):
    def __init__(self, et):
        self.et = et

    def text( self, path, **args ):
        el = self.et.find("./"+path)
        if (el is None) and not args.has_key("default"):
            raise Exception( "Cant find path %s" % path )
        elif (el is None) and args.has_key("default"):
            default = args["default"]
            if type(default) == str:
                return default
            else:
                return default[ args["key"] ]
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

    def append_treecopy( self, other ):
        self.et.append( copy.deepcopy( other.et ) )



class elem(ebase):
    def __init__( self, el ):
        ebase.__init__( self, el )

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

    def set_child_position( self, child, pos ):
        self.et.remove( child.et )
        self.et.insert( pos, child.et )


class etree(ebase):
    def  __init__( self, fname ):
        ebase.__init__( self, ElementTree( file=fname ) )

    def write( self, fname, encoding=None ):
        # Make sure, that we end with a newline
        self.et.getroot().tail = '\n'
        self.et.write(fname, encoding=encoding)

    def tostring (self):
        return self.et.tostring ()

    def ensure_child( self, tag ):
        retval = self.et.find("./"+tag)
        if not retval is None:
            return elem( retval )
        else:
            return elem( SubElement( self.et.getroot(), tag ) )

    def set_child_position( self, child, pos ):
        root = self.et.getroot()
        root.remove( child.et )
        root.insert( pos, child.et )

    def setroot( self, tag ):
        retval = elem( Element (tag) )
        self.et._setroot( retval.et )
        return retval

