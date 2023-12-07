# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017 Linutronix GmbH

import logging
import os
from shutil import copyfile, copytree, rmtree

from elbepack.dump import dump_fullpkgs
from elbepack.elbexml import ElbeXML
from elbepack.repomanager import UpdateRepo
from elbepack.shellhelper import do, system
from elbepack.ziparchives import create_zip_archive


class MissingData(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def inlucdedir(destination, directory, source, mode=None):
    dst = destination + '/' + directory
    copytree(source, dst)
    if mode:
        for dp, _, fn in os.walk(dst):
            for f in fn:
                p = os.path.join(dp, f)
                os.chmod(p, mode)


def gen_update_pkg(project, xml_filename, upd_filename,
                   override_buildtype=None, skip_validate=False, debug=False,
                   cmd_dir=None, cfg_dir=None):

    if xml_filename:
        xml = ElbeXML(xml_filename, buildtype=override_buildtype,
                      skip_validate=skip_validate)

        if not xml.has('fullpkgs'):
            raise MissingData('Xml does not have fullpkgs list')

        if not project.xml.has('fullpkgs'):
            raise MissingData('Source Xml does not have fullpkgs list')

        if not project.buildenv.rfs:
            raise MissingData('Target does not have a build environment')

        cache = project.get_rpcaptcache()

        instpkgs = cache.get_installed_pkgs()
        instindex = {}

        for p in instpkgs:
            instindex[p.name] = p

        xmlpkgs = xml.node('/fullpkgs')
        xmlindex = {}

        fnamelist = []

        for p in xmlpkgs:
            name = p.et.text
            ver = p.et.get('version')

            xmlindex[name] = p

            if name not in instindex:
                logging.info('Package removed: %s', name)
                continue

            ipkg = instindex[name]
            comp = cache.compare_versions(ipkg.installed_version, ver)

            pfname = ipkg.installed_deb

            if comp == 0:
                logging.info('Package ok: %s-%s', name, ipkg.installed_version)
                if debug:
                    fnamelist.append(pfname)
                continue

            if comp > 0:
                logging.info('Package upgrade: %s', pfname)
                fnamelist.append(pfname)
            else:
                logging.info('Package downgrade: %s-%s',
                             name, ipkg.installed_version)

        for p in instpkgs:
            if p.name in xmlindex:
                continue

            logging.info('Package %s newly installed', p.name)
            pfname = p.installed_deb
            fnamelist.append(pfname)

    update = os.path.join(project.builddir, 'update')

    if os.path.exists(update):
        rmtree(update)

    system(f'mkdir -p {update}')

    if xml_filename:
        repodir = os.path.join(update, 'repo')

        repo = UpdateRepo(xml, repodir)

        for fname in fnamelist:
            path = os.path.join(
                project.chrootpath,
                'var/cache/apt/archives',
                fname)
            repo.includedeb(path)

        repo.finalize()

        dump_fullpkgs(project.xml, project.buildenv.rfs, cache)

        project.xml.xml.write(os.path.join(update, 'new.xml'))
        system(f"cp {xml_filename} {os.path.join(update, 'base.xml')}")
    else:
        system('cp source.xml update/new.xml')

    if project.presh_file:
        copyfile(project.presh_file, update + '/pre.sh')
        os.chmod(update + '/pre.sh', 0o755)

    if project.postsh_file:
        copyfile(project.postsh_file, update + '/post.sh')
        os.chmod(update + '/post.sh', 0o755)

    if cmd_dir:
        inlucdedir(update, 'cmd', cmd_dir, mode=0o755)

    if cfg_dir:
        inlucdedir(update, 'conf', cfg_dir)

    create_zip_archive(upd_filename, update, '.')

    if project.postbuild_file:
        logging.info('Postbuild script')
        cmd = (f' "{upd_filename} {project.xml.text("project/version")} '
               f'{project.xml.text("project/name")}"')
        do(project.postbuild_file + cmd, allow_fail=True)
