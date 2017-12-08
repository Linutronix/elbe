<%
import string
ELEM = "{http://www.w3.org/2001/XMLSchema}element"
CPLX = "{http://www.w3.org/2001/XMLSchema}complexType"
DOC  = "{http://www.w3.org/2001/XMLSchema}annotation/{http://www.w3.org/2001/XMLSchema}documentation"
ATTR = "{http://www.w3.org/2001/XMLSchema}attribute"
SEQ  = "{http://www.w3.org/2001/XMLSchema}sequence"
SIMP = "{http://www.w3.org/2001/XMLSchema}simpleType"
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
%>

Elbe XML Schema reference
=========================

<%def name="element(n)">
== ${n.et.attrib["name"]} type: '${n.et.attrib["type"]}' ==

${docindent(n.text(DOC))}
</%def>


<%def name="elementexample(n)">
  <${n.et.attrib["name"]}> ${n.et.attrib["type"]} </${n.et.attrib["name"]}> \
</%def>

<%def name="elementseq(n)">
  ${n.et.attrib["name"]} ${genlink(n.et.attrib["type"])} ${cardinality(n)}::
${docindent(n.text(DOC), 2)}
</%def>

<%def name="complextype(n)">
[[${n.et.attrib["name"]}]]
== TYPE: ${n.et.attrib["name"]} ==

${docindent(n.text(DOC))}

=== Example ===
% if n.has(SEQ):
[xml]
source~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
<${n.et.attrib["name"]}> \
% for s in n.node(SEQ):
% if s.tag == ELEM:
${elementexample(s)} \
% endif
% endfor

</${n.et.attrib["name"]}>
source~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

=== Element description ===
% for s in n.node(SEQ):
% if s.tag == ELEM:
${elementseq(s)}
% endif
% endfor
% else:
 no sequence
% endif
</%def>

<%def name="simpletype(n)">
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
</%def>

<%def name="printnode(n)">
%   if n.tag == ELEM:
${element(n)}
%   elif n.tag == CPLX:
${complextype(n)}
%   elif n.tag == SIMP:
${simpletype(n)}
%   endif
</%def>

<%def name="printnodeseq(n)">
%   if n.tag == ELEM:
${elementseq(n)}
%   elif n.tag == CPLX:
${complextype(n)}
%   elif n.tag == SIMP:
${simpletype(n)}
%   endif
</%def>

% for n in xml.all('./'):
${printnode(n)}
% endfor
