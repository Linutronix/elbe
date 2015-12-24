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


from soaplib.xml import ns, create_xml_element, create_xml_subelement

from soaplib.serializers.primitive import String, Integer
from soaplib.serializers.primitive import Array as OrigArray

class Array(OrigArray):
    """soaplib version in wheezy has a broken Implementattion of
       Array.add_to_schema(). Lets use the correct Implementation
       which also exists in jessie"""

    def add_to_schema(self,schema_dict,nsmap):
        typ = self.get_datatype()
        
        self.serializer.add_to_schema(schema_dict, nsmap)

        if not schema_dict.has_key(typ):

            complexTypeNode = create_xml_element(
                nsmap.get('xs') + 'complexType', nsmap)
            complexTypeNode.set('name',self.get_datatype())

            sequenceNode = create_xml_subelement(
                complexTypeNode, nsmap.get('xs') + 'sequence')
            elementNode = create_xml_subelement(
                sequenceNode, nsmap.get('xs') + 'element')
            elementNode.set('minOccurs','0')
            elementNode.set('maxOccurs','unbounded')
            elementNode.set('type',
                "%s:%s" % (self.serializer.get_namespace_id(), self.serializer.get_datatype()))
            elementNode.set('name',self.serializer.get_datatype())

            typeElement = create_xml_element(
                nsmap.get('xs') + 'element', nsmap)
            typeElement.set('name',typ)
            typeElement.set('type',
                "%s:%s" % (self.namespace_id, self.get_datatype()))
            
            schema_dict['%sElement'%(self.get_datatype(nsmap))] = typeElement
            schema_dict[self.get_datatype(nsmap)] = complexTypeNode


