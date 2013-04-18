#!/usr/bin/env python

import subprocess
import os

from distutils.core import setup
from distutils.command.install import install

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
            envvars = dict({"prefix": self.prefix, "DESTDIR": self.root}, **dict(os.environ))
        else:
            envvars = dict({"prefix": self.prefix}, **dict(os.environ))


        docs_dir = abspath("./docs/")

        output = subprocess.Popen("make install",
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  cwd=docs_dir,
                                  env=envvars).communicate()[0]
        print output

setup(name='elbe',
      version='0.5.0',
      description='RootFS builder',
      author='Torben Hohn',
      author_email='torbenh@linutronix.de',
      url='http://elbe-rfs.org/',
      packages=['elbepack'],
      package_data = {'elbepack': ["mako/*.mako", "dbsfed.xsd", "default-preseed.xml", "xsdtoasciidoc.mako"] },
      scripts=['elbe'],
      cmdclass={"install": my_install},
      data_files=[('/usr/share/doc/elbe/examples',['examples/arm-example.xml', 'examples/arm-complex-example.xml', 'examples/amd64-example.xml', 'examples/i386-example.xml'])]
)

