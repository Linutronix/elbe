# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2015, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2015 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Benedikt Spranger <b.spranger@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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

SP_ARTICLES= elbeoverview-en quickstart elbe-schema-reference

DOC_HTML+=$(patsubst %,%.html,$(SP_ARTICLES))

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

sphinx:
	sphinx-build . _build

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
	$(RM) -r _build
	$(RM) article*.rst elbe*.rst *.xml *.xml+ *.html *.html+ *.1 *.5 *.7
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
	$(ASCIIDOC) -d article -b docbook -agit_version=$(ELBE_VERSION) -o $@ $< && \
	pandoc -r docbook -w rst -o $*.rst $@
	sed -i "1s/^/************************\n\n/" $*.rst
	sed -i "1s/^/$*\n/" $*.rst
	sed -i "1s/^/************************\n/" $*.rst
	$(ASCIIDOC) -b docbook -d manpage -f asciidoc.conf \
		$(ASCIIDOC_EXTRA) -agit_version=$(ELBE_VERSION) -o $@+ $< && \
	mv $@+ $@

%.svg : %.dia
	$(RM) $@ && \
	$(DIA) --export=$@ $<

%.png : %.dia
	$(RM) $@ && \
	$(DIA) --export=$@ $<

elbeoverview-en.html : elbeoverview-en.txt elbe-process.png emu-process.png
	$(ASCIIDOC) -d article -b docbook -agit_version=$(ELBE_VERSION) -o elbeoverview-en.xml $< && \
	pandoc -r docbook -w rst -o article-elbeoverview-en.rst elbeoverview-en.xml
	sed -i "1s/^/************************\n\n/" article-elbeoverview-en.rst
	sed -i "1s/^/ELBE Overview\n/" article-elbeoverview-en.rst
	sed -i "1s/^/************************\n/" article-elbeoverview-en.rst
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbeoverview-en.txt

quickstart.html : quickstart.txt
	$(ASCIIDOC) -d article -b docbook -agit_version=$(ELBE_VERSION) -o quickstart.xml $< && \
	pandoc -r docbook -w rst -o article-quickstart.rst quickstart.xml
	sed -i "1s/^/************************\n\n/" article-quickstart.rst
	sed -i "1s/^/ELBE Quickstart\n/" article-quickstart.rst
	sed -i "1s/^/************************\n/" article-quickstart.rst
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 quickstart.txt

elbeoverview-en-ie.html: elbeoverview-en.txt elbe-process.png emu-process.png
	$(ASCIIDOC) -d article -b docbook -agit_version=$(ELBE_VERSION) -o $*.xml $< && \
	pandoc -r docbook -w rst -o article-$*.rst $*.xml
	sed -i "1s/^/************************\n\n/" $*.rst
	sed -i "1s/^/$*\n/" $*.rst
	sed -i "1s/^/************************\n/" $*.rst
	$(ASCIIDOC) -b html5 -a icons -a toc2 -a theme=flask -o elbeoverview-en.html elbeoverview-en.txt

elbe-schema-reference.txt: ../schema/dbsfed.xsd ../elbepack/xsdtoasciidoc.mako
	../elbe xsdtoasciidoc --output elbe-schema-reference.txt ../schema/dbsfed.xsd
	$(ASCIIDOC) -a toc2 $(ASCIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbe-schema-reference.txt

elbe-schema-reference.html: %.html : %.txt
	$(ASCIIDOC) -d article -b docbook -agit_version=$(ELBE_VERSION) -o $*.xml $< && \
	pandoc -r docbook -w rst -o article-$*.rst $*.xml
	sed -i "1s/^/*************************\n\n/" article-$*.rst
	sed -i "1s/^/ELBE XML Reference\n/" article-$*.rst
	sed -i "1s/^/*************************\n/" article-$*.rst
	sed -i "s/<#/<#type-/g" article-$*.rst
	$(ASCIIDOC) -a toc $(ASCIIDOC_EXTRA) -b xhtml11 $*.txt

elbe-examples.txt:
	./build-example-doc.sh
	$(ASCIIDOC) $(ASIIDOC_EXTRA) $(ASCIIDOC_DATA_URI) -b xhtml11 elbe-examples.txt
