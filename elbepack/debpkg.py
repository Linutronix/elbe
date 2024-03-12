# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014, 2017 Linutronix GmbH

import os
import shutil
import string
import subprocess
import tempfile

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
    f = open(fname, 'w')
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

    with tempfile.TemporaryDirectory() as tmpdir:
        pkgfname = f'{name}_{version}_{arch}'
        pkgdir = os.path.join(tmpdir, pkgfname)

        os.makedirs(os.path.join(pkgdir, 'DEBIAN'), exist_ok=True)
        write_file(
            os.path.join(
                pkgdir,
                'DEBIAN',
                'control'),
            0o644,
            gen_controlfile(
                name,
                version,
                arch,
                description,
                deps))

        for (fname, instpath) in files:
            full_instpath = os.path.join(pkgdir, instpath)
            os.makedirs(full_instpath, exist_ok=True)
            shutil.copyfile(fname, full_instpath)

        subprocess.run(['dpkg-deb', '--build', pkgdir], check=True)
        shutil.copyfile(os.path.join(tmpdir, pkgfname + '.deb'), target_dir)

    return pkgfname + '.deb'
