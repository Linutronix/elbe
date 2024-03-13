#!/usr/bin/env python3
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2013-2014, 2017-2018 Linutronix GmbH

import os
import subprocess

from elbepack.version import elbe_version

from setuptools import setup
from setuptools.command.install import install


def abspath(path):
    """ method to determine absolute path
for a relative path inside project's directory."""

    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), path))


class my_install(install):

    def run(self):
        install.run(self)
        if self.root:
            envvars = dict({'prefix': self.prefix,
                            'DESTDIR': self.root},
                           **dict(os.environ))
        else:
            envvars = dict({'prefix': self.prefix}, **dict(os.environ))

        docs_dir = abspath('./docs/')

        output = subprocess.Popen('make install',
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
                'elbepack.schema',
                ],
      package_data={'elbepack': ['makofiles/*.mako',
                                 'init/*.mako',
                                 'init/*.xml',
                                 'default-preseed.xml',
                                 'xsdtoasciidoc.mako',
                                 'schema/dbsfed.xsd',
                                 'schema/xml.xsd']},
      scripts=['elbe'],
      cmdclass={'install': my_install},
      install_requires=['lxml',
                        'Mako',
                        'passlib',
                        'pycdlib',
                        'python-debian',
                        'suds-community']
      )
