# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
# Copyright (c) 2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import errno
import logging
from os import path, remove
from shutil import rmtree, copytree, move
from apt.package import FetchError
from elbepack.repomanager import RepoBase, RepoAttributes


class ArchiveRepo(RepoBase):
    def __init__(self, xml, pathname, origin, description, components):

        # pylint: disable=too-many-arguments

        arch = xml.text("project/arch", key="arch")
        codename = xml.text("project/suite")

        repo_attrs = RepoAttributes(codename, arch, components)

        RepoBase.__init__(self,
                          pathname,
                          None,
                          repo_attrs,
                          description,
                          origin)


def gen_binpkg_archive(ep, repodir):
    repopath = path.join(ep.builddir, repodir)

    try:
        rmtree(repopath)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    # Create archive directory for packages we have to download
    ep.buildenv.rfs.mkdir_p('/var/cache/elbe/pkgarchive')

    try:
        # Repository containing all packages currently installed
        repo = ArchiveRepo(ep.xml, repopath, "Elbe",
                           "Elbe package archive", ["main"])

        c = ep.get_rpcaptcache()
        pkglist = c.get_installed_pkgs()

        for pkg in pkglist:
            # Use package from local APT archive, if the file exists
            filename = pkg.installed_deb
            rel_path = path.join('var/cache/apt/archives', filename)
            abs_path = ep.buildenv.rfs.fname(rel_path)

            if not path.isfile(abs_path):
                # Package file does not exist, download it and adjust path name
                logging.warning('Package file "%s" not found in var/cache/apt/archives, downloading it',
                                filename)
                abs_path = ep.buildenv.rfs.fname(rel_path)
                pkg_id = "%s-%s" % (pkg.name, pkg.installed_version)
                try:
                    abs_path = c.download_binary(pkg.name,
                                                 '/var/cache/elbe/pkgarchive',
                                                 pkg.installed_version)
                except ValueError:
                    logging.error('No package "%s"', pkg_id)
                    raise
                except FetchError:
                    logging.error('Package "%s" could not be downloaded', pkg_id)
                    raise
                except TypeError:
                    logging.error('Package "%s" missing name or version', pkg_id)
                    raise

            # Add package to repository
            # XXX Use correct component
            repo.includedeb(abs_path, "main")

        repo.finalize()

    finally:
        rmtree(ep.buildenv.rfs.fname('var/cache/elbe/pkgarchive'))
        repo.finalize()


def checkout_binpkg_archive(ep, repodir):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

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
            logging.info("Copying package archive into build environment")
            copytree(repopath, pkgarchive)

            # Move original etc/apt/sources.list and etc/apt/sources.list.d out
            # of the way
            logging.info("Moving original APT configuration out of the way")
            if path.isfile(sources_list):
                move(sources_list, sources_list_backup)
            if path.isdir(sources_list_d):
                move(sources_list_d, sources_list_d_backup)

            # Now create our own, with the package archive being the only
            # source
            logging.info("Creating new /etc/apt/sources.list")
            deb = "deb file:///var/cache/elbe/pkgarchive "
            deb += ep.xml.text("/project/suite")
            deb += " main"
            with open(sources_list, 'w') as f:
                f.write(deb)

            # We need to update the APT cache to apply the changed package
            # source
            logging.info("Updating APT cache to use package archive")
            ep.drop_rpcaptcache()
            c = ep.get_rpcaptcache()
            c.update()

            # Iterate over all packages, and mark them for installation or
            # deletion, using the same logic as in commands/updated.py
            logging.info("Calculating packages to install/remove")
            fpl = ep.xml.node("fullpkgs")
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
            logging.info("Commiting package changes")
            c.commit()
        finally:
            # If we changed the package sources, move back the backup
            if path.isdir(sources_list_d_backup) or \
                    path.isfile(sources_list_backup):
                logging.info("Moving back original APT configuration")
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
                logging.info("Removing package archive from build environment")
                rmtree(pkgarchive)

            # Update APT cache, if we modified the package sources
            if update_needed:
                logging.info("Updating APT cache to use original package sources")
                ep.drop_rpcaptcache()
                ep.get_rpcaptcache().update()
