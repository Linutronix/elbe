# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2017 Linutronix GmbH

import logging
from os import path, remove
from shutil import copytree, move, rmtree

from elbepack.repomanager import RepoAttributes, RepoBase


class ArchiveRepo(RepoBase):
    def __init__(self, xml, pathname, origin, description, components):

        arch = xml.text('project/arch', key='arch')
        codename = xml.text('project/suite')

        repo_attrs = RepoAttributes(codename, arch, components)

        RepoBase.__init__(self,
                          pathname,
                          None,
                          repo_attrs,
                          description,
                          origin)


def checkout_binpkg_archive(ep, repodir):

    repopath = path.join(ep.builddir, repodir)
    sources_list = ep.buildenv.rfs.fname('etc/apt/sources.list')
    sources_list_d = ep.buildenv.rfs.fname('etc/apt/sources.list.d')
    sources_list_backup = path.join(ep.builddir, 'sources.list.orig')
    sources_list_d_backup = path.join(ep.builddir, 'sources.list.d.orig')
    pkgarchive = ep.buildenv.rfs.fname('var/cache/elbe/pkgarchive')

    with ep.buildenv:
        try:
            # Copy the package archive into the buildenv,
            # so the RPCAptCache can access it
            logging.info('Copying package archive into build environment')
            copytree(repopath, pkgarchive)

            # Move original etc/apt/sources.list and etc/apt/sources.list.d out
            # of the way
            logging.info('Moving original APT configuration out of the way')
            if path.isfile(sources_list):
                move(sources_list, sources_list_backup)
            if path.isdir(sources_list_d):
                move(sources_list_d, sources_list_d_backup)

            # Now create our own, with the package archive being the only
            # source
            logging.info('Creating new /etc/apt/sources.list')
            deb = 'deb file:///var/cache/elbe/pkgarchive '
            deb += ep.xml.text('/project/suite')
            deb += ' main'
            with open(sources_list, 'w') as f:
                f.write(deb)

            # We need to update the APT cache to apply the changed package
            # source
            logging.info('Updating APT cache to use package archive')
            ep.drop_rpcaptcache()
            c = ep.get_rpcaptcache()
            c.update()

            # Iterate over all packages, and mark them for installation or
            # deletion, using the same logic as in commands/updated.py
            logging.info('Calculating packages to install/remove')
            fpl = ep.xml.node('fullpkgs')
            pkgs = c.get_pkglist('all')

            for p in pkgs:
                marked = False
                for fpi in fpl:
                    if p.name == fpi.et.text:
                        version = fpi.et.get('version')
                        logging.info('Install "%s-%s"', p.name, version)
                        c.mark_install(p.name, version,
                                       from_user=not fpi.et.get('auto'),
                                       nodeps=True)
                        marked = True

                if not marked:
                    logging.info('Delete "%s-%s"', p.name, version)
                    c.mark_delete(p.name)

            # Now commit the changes
            logging.info('Commiting package changes')
            c.commit()
        finally:
            # If we changed the package sources, move back the backup
            if path.isdir(sources_list_d_backup) or \
                    path.isfile(sources_list_backup):
                logging.info('Moving back original APT configuration')
                update_needed = True
            else:
                update_needed = False

            if path.isdir(sources_list_d_backup):
                move(sources_list_d_backup, sources_list_d)

            if path.isfile(sources_list_backup):
                if path.isfile(sources_list):
                    remove(sources_list)
                move(sources_list_backup, sources_list)

            # Remove the package archive from the buildenv
            if path.isdir(pkgarchive):
                logging.info('Removing package archive from build environment')
                rmtree(pkgarchive)

            # Update APT cache, if we modified the package sources
            if update_needed:
                logging.info('Updating APT cache to use original package sources')
                ep.drop_rpcaptcache()
                ep.get_rpcaptcache().update()
