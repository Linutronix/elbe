#!/usr/bin/env python

import subprocess
import os
import glob

from distutils.core import setup
from distutils.command.install import install

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
      version=elbe_version,
      description='RootFS builder',
      author='Torben Hohn',
      author_email='torbenh@linutronix.de',
      url='http://elbe-rfs.org/',
      packages=['elbepack', \
'elbepack.commands', 'elbepack.daemons', 'elbepack.daemons.soap', ],
      package_data = {'elbepack': ["mako/*.mako", "init/*.mako" ,"dbsfed.xsd", \
"default-preseed.xml", "xsdtoasciidoc.mako"] },
      scripts=['elbe'],
      cmdclass={"install": my_install},
      data_files= [
          ('/usr/share/doc/elbe-doc/', glob.glob("docs/elbe-schema-reference*")),
          ('/usr/share/doc/elbe-doc/', glob.glob("docs/elbeoverview-en*")),
          ('/usr/share/doc/elbe-doc/examples', glob.glob("examples/*xml"))],
)
