# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import string

from tempfile import mkdtemp

control_template_string = """Package: ${name}
Version: ${version}
Section: main
Priority: optional
Architecture: ${arch}
Maintainer: elbe-devel@linutronix.de
Description: ${description}
Depends: ${deps}
Multi-Arch: same
"""

control_template = string.Template(control_template_string)


def gen_controlfile(name, version, arch, description, deps):
    d = dict(
        name=name,
        version=version,
        arch=arch,
        description=description,
        deps=deps)
    return control_template.substitute(d)


def write_file(fname, mode, cont):
    f = file(fname, "w")
    f.write(cont)
    f.close()
    os.chmod(fname, mode)


def build_binary_deb(
        name,
        arch,
        version,
        description,
        files,
        deps,
        target_dir):

    # pylint: disable=too-many-arguments

    tmpdir = mkdtemp()
    pkgfname = "%s_%s_%s" % (name, version, arch)
    pkgdir = os.path.join(tmpdir, pkgfname)

    os.system('mkdir -p "%s"' % os.path.join(pkgdir, "DEBIAN"))
    write_file(
        os.path.join(
            pkgdir,
            "DEBIAN",
            "control"),
        0o644,
        gen_controlfile(
            name,
            version,
            arch,
            description,
            deps))

    for (fname, instpath) in files:
        full_instpath = os.path.join(pkgdir, instpath)
        os.system('mkdir -p "%s"' % full_instpath)
        os.system('cp -a "%s" "%s"' % (fname, full_instpath))

    os.system('dpkg-deb --build "%s"' % pkgdir)

    os.system(
        'cp -v "%s" "%s"' %
        (os.path.join(
            tmpdir,
            pkgfname +
            ".deb"),
            target_dir))

    os.system('rm -r "%s"' % tmpdir)

    return pkgfname + ".deb"
