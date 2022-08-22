#!/usr/bin/env python3
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013, 2017-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Sebastian Andrzej Siewior <bigeasy@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess
import os
import glob

from setuptools import setup
from setuptools.command.install import install

from elbepack.version import elbe_version


def abspath(path):
    """A method to determine absolute path
for a relative path inside project's directory."""

    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), path))


class my_install(install):

    def run(self):
        install.run(self)
        if self.root:
            envvars = dict({"prefix": self.prefix,
                            "DESTDIR": self.root},
                           **dict(os.environ))
        else:
            envvars = dict({"prefix": self.prefix}, **dict(os.environ))

        docs_dir = abspath("./docs/")

        output = subprocess.Popen("make install",
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  cwd=docs_dir,
                                  env=envvars).communicate()[0]
        print(output)


setup(name='elbe',
      version=elbe_version,
      description='RootFS builder',
      author='Linutronix GmbH',
      author_email='info@linutronix.de',
      url='http://elbe-rfs.org/',
      packages=['elbepack',
                'elbepack.commands',
                'elbepack.daemons',
                'elbepack.daemons.soap',
                'elbepack.debianize',
                'elbepack.debianize.panels',
                'elbepack.debianize.widgets',
                'elbepack.debianize.base',
                ],
      package_data={'elbepack': ["makofiles/*.mako",
                                 "makofiles/debianize/*/*.mako",
                                 "makofiles/debianize/*/*.install",
                                 "makofiles/debianize/*/*.links",
                                 "makofiles/debianize/*/copyright",
                                 "init/*.mako",
                                 "init/*.xml",
                                 "default-preseed.xml",
                                 "xsdtoasciidoc.mako"],
                    'schema': ["dbsfed.xsd", "xml.xsd"]},
      scripts=['elbe'],
      cmdclass={"install": my_install},
      data_files=[
          ('/usr/share/doc/elbe-doc/',
           glob.glob("docs/elbe-schema-reference*")),
          ('/usr/share/doc/elbe-doc/',
           glob.glob("docs/elbeoverview-en*")),
          ('/usr/share/doc/elbe-doc/contrib/linux',
           glob.glob("contrib/linux/*")),
          ('/usr/share/doc/elbe-doc/examples',
           glob.glob("examples/*xml")),
          ('/usr/share/doc/elbe-doc/examples/includes/prod',
           glob.glob("examples/includes/prod/*.xml")),
          ('/usr/share/doc/elbe-doc/examples/includes/devel',
           glob.glob("examples/includes/devel/*.xml"))],
      )
