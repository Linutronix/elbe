# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2015, 2017-2018 Linutronix GmbH

prefix?=$(HOME)
htmldir?=$(prefix)/share/doc/elbe
mandir?=$(prefix)/share/man
man1dir=$(mandir)/man1

sphinxbuilddir?=_build
sphinxflags?=-W

INSTALL?=install
RM ?= rm -f
CP ?= cp

all: sphinx

sphinx:
	sphinx-build $(sphinxflags) -b man  . $(sphinxbuilddir)/man
	sphinx-build $(sphinxflags) -b html . $(sphinxbuilddir)/html

install-sphinx: sphinx
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(sphinxbuilddir)/man/* $(DESTDIR)$(man1dir)

	$(INSTALL) -d -m 755 $(DESTDIR)$(htmldir)
	$(CP) -r $(sphinxbuilddir)/html/ $(DESTDIR)$(htmldir)

install: install-sphinx

clean:
	$(RM) -r $(sphinxbuilddir)
