## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2013, 2017 Manuel Traut <manut@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
<%
import string
ELEM = "{http://www.w3.org/2001/XMLSchema}element"
CPLX = "{http://www.w3.org/2001/XMLSchema}complexType"
DOC  = "{http://www.w3.org/2001/XMLSchema}annotation/{http://www.w3.org/2001/XMLSchema}documentation"
ATTR = "{http://www.w3.org/2001/XMLSchema}attribute"
SEQ  = "{http://www.w3.org/2001/XMLSchema}sequence"
SIMP = "{http://www.w3.org/2001/XMLSchema}simpleType"
GRP  = "{http://www.w3.org/2001/XMLSchema}group"
RSTR = "{http://www.w3.org/2001/XMLSchema}restriction"
MAXI = "{http://www.w3.org/2001/XMLSchema}maxInclusive"
MINI = "{http://www.w3.org/2001/XMLSchema}minInclusive"

def docindent( s, indent=0 ):
  lines = s.splitlines()
  lines = [l.strip() for l in lines]
  lines = map(lambda x: indent*" "+x, lines)
  return str('').join(lines).strip()

def genlink(typ):
  if typ.startswith("rfs:"):
    return "<<"+typ[4:]+","+typ+">>"
  else:
    return typ

def stripscheme(s):
  scheme = "{http://www.w3.org/2001/XMLSchema}"
  if s.startswith(scheme):
    return s[len(scheme):]
  else:
    return s

def cardinality(e):
  min = None
  max = None 

  retval = ""

  if e.et.attrib.has_key('minOccurs'):
    min = e.et.attrib['minOccurs']

  if e.et.attrib.has_key('maxOccurs'):
    min = e.et.attrib['maxOccurs']

  if min=="0":
    retval += "*optional* "

  if max=="1" and min=="1":
    retval += "*mandatory"

  return retval

def element_example(n):
    name = n.et.attrib["name"]
    _type = n.et.attrib["type"]
    return "<%s> %s </%s>" % (name, _type, name)

def doc(e):
    if e.has(".//%s" % DOC):
        return docindent(e.text(".//%s" % DOC), 2)
    return ""

def element_doc(e):
    name = e.et.attrib["name"]
    _type = e.et.attrib["type"]
    return "%s %s %s::\n%s" % (name,
                               genlink(_type),
                               cardinality(n),
                               doc(e))
def attr_doc(a):
    if "name" in a.et.attrib:
        return "[attr] %s" % element_doc(a)
    return ""
%>\
##
<%def name="do_element(n)">
== ${n.et.attrib["name"]} type: '${n.et.attrib["type"]}' ==

${docindent(n.text(DOC))}
</%def>\
##
<%def name="do_simple(n)">
[[${n.et.attrib["name"]}]]
==  SIMPLE TYPE: ${n.et.attrib["name"]} ==

${docindent(n.text(DOC))}

%if n.has(RSTR):
=== Base Type === 
'${n.node(RSTR).et.attrib["base"]}'


=== Restrictions ===

[width="60%"]
|=====================================
%for r in n.node(RSTR):
| '${stripscheme(r.tag)}' | ${r.et.attrib["value"]} 
%endfor
|=====================================
%endif
</%def>\
##
<%def name="do_group(n)">
[[${n.et.attrib["name"]}]]
==  GROUP : ${n.et.attrib["name"]} ==

${docindent(n.text(DOC))}


% for e in n.all(".//%s" % ELEM):
${printnode(e)}
% endfor

</%def>\
##
<%def name="printnode(n)">
%   if n.tag == ELEM:
${do_element(n)}
%   elif n.tag == SIMP:
${do_simple(n)}
%   elif n.tag == CPLX:
${do_complex(n)}
%   elif n.tag == GRP:
${do_group(n)}
%   endif
</%def>\
##
<%def name="do_complex(n)">
[[${n.et.attrib["name"]}]]
== TYPE: ${n.et.attrib["name"]} ==

${docindent(n.text(DOC))}

=== Example ===
[xml]
source~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<${n.et.attrib["name"]}>\
% for e in n.all(".//%s" % ELEM):

  ${element_example(e)}
% endfor

% for ref in n.all(".//%s" % GRP):
% for g in xml.all('./%s[@name="%s"]' % (GRP, ref.et.attrib["ref"].strip("rfs:"))):
% for e in g.all(".//%s" % ELEM):
  ${element_example(e)}
% endfor
% endfor
% endfor
</${n.et.attrib["name"]}>
source~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

=== Elements description ===

% for a in n.all(".//%s" % ATTR):
${attr_doc(a)}

% endfor
% for e in n.all(".//%s" % ELEM):
${element_doc(e)}

% endfor
</%def>\
##
Elbe XML Schema reference
=========================
% for n in xml.all('./'):
${printnode(n)}\
% endfor
