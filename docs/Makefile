ELBE_VERSION=$(`../elbe --version | awk '{ print $2 }'`)

MAN1_TXT= \
	$(filter-out $(addsuffix .txt, $(ARTICLES) $(SP_ARTICLES)), \
		$(wildcard elbe-*.txt)) \
	elbe.txt
MAN5_TXT=
MAN7_TXT=

MAN_TXT = $(MAN1_TXT) $(MAN5_TXT) $(MAN7_TXT)
MAN_XML=$(patsubst %.txt,%.xml,$(MAN_TXT))
MAN_HTML=$(patsubst %.txt,%.html,$(MAN_TXT))

DOC_HTML=$(MAN_HTML)

ARTICLES = elbe-schema-reference elbe-examples
SP_ARTICLES= elbeoverview-en repobuilder-en quickstart

DOC_HTML+=$(patsubst %,%.html,$(ARTICLES) $(SP_ARTICLES))

DOC_MAN1=$(patsubst %.txt,%.1,$(MAN1_TXT))
DOC_MAN5=$(patsubst %.txt,%.5,$(MAN5_TXT))
DOC_MAN7=$(warning $(DOC_HTML)) $(patsubst %.txt,%.7,$(MAN7_TXT))

prefix?=$(HOME)
bindir?=$(prefix)/bin
htmldir?=$(prefix)/share/doc/elbe
pdfdir?=$(prefix)/share/doc/elbe
mandir?=$(prefix)/share/man
man1dir=$(mandir)/man1
man5dir=$(mandir)/man5
man7dir=$(mandir)/man7

MAN_BASE_URL = file://$(htmldir)/

ASCIIDOC=asciidoc
ASCIIDOC_EXTRA =
MANPAGE_XSL = manpage-normal.xsl
XMLTO_EXTRA =
INSTALL?=install
RM ?= rm -f
DIA ?= dia

DOCBOOK_XSL_172=1

ifdef DOCBOOK_XSL_172
ASCIIDOC_EXTRA += -a git-asciidoc-no-roff -a max-width=55em -a icons -a images
MANPAGE_XSL = manpage-1.72.xsl
else
ASCIIDOC_EXTRA += -a git-asciidoc-no-roff -a data-uri -a max-width=55em -a data-uri 
endif

ASCIIDOC_DATA_URI = -a data-uri -a iconsdir=/usr/share/asciidoc/images/icons

all: html man
html: $(DOC_HTML)

install: install-man install-html

install-man: man
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(DOC_MAN1) $(DESTDIR)$(man1dir)

install-html:
	$(INSTALL) -d -m 755 $(DESTDIR)$(htmldir)
	$(INSTALL) -m 644 $(DOC_HTML) $(DESTDIR)$(htmldir)

$(DOC_HTML) $(DOC_MAN1) $(DOC_MAN5) $(DOC_MAN7): asciidoc.conf

man: man1 man5 man7
man1: $(DOC_MAN1)
man5: $(DOC_MAN5)
man7: $(DOC_MAN7)


clean:
	$(RM) *.xml *.xml+ *.html *.html+ *.1 *.5 *.7
	$(RM) *.texi *.texi+ *.texi++ git.info gitman.info
	$(RM) *.pdf
	$(RM) howto-index.txt howto/*.html doc.dep
	$(RM) technical/api-*.html technical/api-index.txt
	$(RM) $(cmds_txt) *.made
	$(RM) manpage-base-url.xsl
	$(RM) elbe-examples.txt elbe-examples.html

$(MAN_HTML): %.html : %.txt
	$(RM) $@+ $@ && \
	$(ASCIIDOC) -b xhtml11 -d manpage -f asciidoc.conf \
		$(ASCIIDOC_EXTRA) -agit_version=$(ELBE_VERSION) -o $@+ $< && \
	mv $@+ $@

manpage-base-url.xsl: manpage-base-url.xsl.in
	sed "s|@@MAN_BASE_URL@@|$(MAN_BASE_URL)|" $< > $@

%.1 %.5 %.7 : %.xml manpage-base-url.xsl
	$(RM) $@ && \
	xmlto -m $(MANPAGE_XSL) $(XMLTO_EXTRA) man $<

%.xml : %.txt
	$(RM) $@+ $@ && \
	$(ASCIIDOC) -b docbook -d manpage -f asciidoc.conf \
		$(ASCIIDOC_EXTRA) -agit_version=$(ELBE_VERSION) -o $@+ $< && \
	mv $@+ $@

$(patsubst %,%.html,$(ARTICLES)) : %.html : %.txt
	$(ASCIIDOC) -a toc $(ASCIIDOC_EXTRA) -b xhtml11 $*.txt

%.svg : %.dia
	$(RM) $@ && \
	$(DIA) --export=$@ $<

%.png : %.dia
	$(RM) $@ && \
	$(DIA) --export=$@ $<

elbeoverview-en.html : elbeoverview-en.txt elbe-process.png emu-process.png
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbeoverview-en.txt

quickstart.html : quickstart.txt
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 quickstart.txt

elbeoverview-en-ie.html: elbeoverview-en.txt elbe-process.png emu-process.png
	$(ASCIIDOC) -b html5 -a icons -a toc2 -a theme=flask -o elbeoverview-en.html elbeoverview-en.txt

elbe-schema-reference.txt: ../elbepack/dbsfed.xsd ../elbepack/xsdtoasciidoc.mako
	../elbe xsdtoasciidoc --output elbe-schema-reference.txt ../elbepack/dbsfed.xsd
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbe-schema-reference.txt

elbe-examples.txt:
	./build-example-doc.sh
	$(ASCIIDOC) $(ASIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbe-examples.txt

repobuilder-en.html : repobuilder-en.txt buildrepo.png repobuild-cycle.png
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 repobuilder-en.txt
