# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014-2015 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Andreas Messerschmid <andreas@linutronix.de>
# Copyright (c) 2014-2018 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014 Stefan Gast <stefan.gast@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# pylint: disable=too-many-lines

from __future__ import print_function

import os
import errno
import re
import glob

from datetime import datetime
from shutil import (rmtree, copyfile, copyfileobj)
from contextlib import contextmanager
from threading import Thread

from passlib.hash import pbkdf2_sha512

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, ForeignKey)
from sqlalchemy import (Integer, String, Boolean, Sequence, DateTime)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import (ElbeXML, ValidationMode)
from elbepack.dosunix import dos2unix
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

Base = declarative_base()


class ElbeDBError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class InvalidLogin(Exception):
    def __init__(self):
        Exception.__init__(self, "Invalid login")


@contextmanager
def session_scope(session):
    try:
        yield session
        try:
            session.commit()
        except OperationalError as e:
            raise ElbeDBError("database commit failed: " + str(e))
    except BaseException:
        session.rollback()
        raise
    finally:
        session.remove()


def get_versioned_filename(name, version, suffix):
    return quote(name, ' ') + '_' + quote(version, ' ') + suffix


def _update_project_file(s, builddir, name, mime_type, description):

    # pylint: disable=too-many-arguments

    filename = os.path.join(builddir, name)
    try:
        f = s.query(ProjectFile).\
            filter(ProjectFile.builddir == builddir).\
            filter(ProjectFile.name == name).one()
    except NoResultFound:
        if os.path.isfile(os.path.join(builddir, name)):
            f = ProjectFile(builddir=builddir,
                            name=name,
                            mime_type=mime_type,
                            description=description)
            s.add(f)
            return filename
        return None

    if os.path.isfile(filename):
        f.mime_type = mime_type
        f.description = description
    else:
        s.delete(f)
        return None

    return filename


class ElbeDB(object):

    # pylint: disable=too-many-public-methods

    db_path = '/var/cache/elbe'
    db_location = 'sqlite:///' + db_path + '/elbe.db'

    def __init__(self):
        engine = create_engine(self.__class__.db_location,
                               connect_args={'timeout': 30})
        Base.metadata.create_all(engine)
        smaker = sessionmaker(bind=engine)
        self.session = scoped_session(smaker)

    def list_users(self):
        with session_scope(self.session) as s:
            res = s.query(User).all()
            ret = []
            for u in res:
                ret.append(UserData(u))
            return ret

    def list_projects(self):
        with session_scope(self.session) as s:
            res = s.query(Project).all()
            ret = []
            for p in res:
                ret.append(ProjectData(p))
            return ret

    def list_projects_of(self, userid):
        with session_scope(self.session) as s:
            res = s.query(Project).filter(Project.owner_id == userid).all()
            ret = []
            for p in res:
                ret.append(ProjectData(p))
            return ret

    def get_project_data(self, builddir):
        # Can throw: ElbeDBError
        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            return ProjectData(p)

    def set_postbuild(self, builddir, postbuild_file):
        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot set postbuild file while project %s is busy" %
                    builddir)

            p.edit = datetime.utcnow()

            with open(builddir + "/postbuild.sh", 'w') as dst:
                copyfileobj(postbuild_file, dst)

            os.chmod(builddir + "/postbuild.sh", 0o755)
            dos2unix(builddir + "/postbuild.sh")

            return _update_project_file(s, builddir,
                "postbuild.sh", "application/sh", "postbuild script")

    def set_savesh(self, builddir, savesh_file):
        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot set savesh file while project %s is busy" %
                    builddir)

            p.edit = datetime.utcnow()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            with open(builddir + "/save.sh", 'w') as dst:
                copyfileobj(savesh_file, dst)

            os.chmod(builddir + "/save.sh", 0o755)
            dos2unix(builddir + "/save.sh")

            return _update_project_file(
                s, builddir,
                "save.sh", "application/sh", "version save script")

    def set_presh(self, builddir, presh_file):
        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot set presh file while project %s is busy" %
                    builddir)

            p.edit = datetime.utcnow()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            with open(builddir + "/pre.sh", 'w') as dst:
                copyfileobj(presh_file, dst)

            dos2unix(builddir + "/pre.sh")

            return _update_project_file(
                s, builddir, "pre.sh", "application/sh", "pre install script")

    def set_postsh(self, builddir, postsh_file):
        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot set postsh file while project %s is busy" %
                    builddir)

            p.edit = datetime.utcnow()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            with open(builddir + "/post.sh", 'w') as dst:
                copyfileobj(postsh_file, dst)

            dos2unix(builddir + "/post.sh")

            return _update_project_file(
                s, builddir,
                "post.sh", "application/sh", "post install script")

    def set_xml(self, builddir, xml_file):
        # This method can throw: ElbeDBError, ValidationError, OSError

        if not os.path.exists(builddir):
            raise ElbeDBError("project directory does not exist")

        srcxml_fname = os.path.join(builddir, "source.xml")

        if xml_file is None:
            xml_file = srcxml_fname

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot set XML file while project %s is busy" %
                    builddir)

            xml = ElbeXML(
                xml_file,
                url_validation=ValidationMode.NO_CHECK)  # ValidationError

            p.name = xml.text("project/name")
            p.version = xml.text("project/version")
            p.edit = datetime.utcnow()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            if xml_file != srcxml_fname:
                copyfile(xml_file, srcxml_fname)  # OSError

            _update_project_file(
                s,
                builddir,
                "source.xml",
                "application/xml",
                "ELBE recipe of the project")

    # TODO what about source.xml ? stored always in db ? version management ?
    #       build/needs_build state ? locking ?

    def create_project(self, builddir, owner_id=None):
        # Throws: ElbeDBError, OSError
        directory_created = False

        try:
            with session_scope(self.session) as s:
                if s.query(Project).\
                        filter(Project.builddir == builddir).count() > 0:
                    raise ElbeDBError("project %s already exists in database" %
                                      builddir)

                try:
                    os.makedirs(builddir)  # OSError
                    directory_created = True
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        raise ElbeDBError(
                            "project directory %s already exists" %
                            builddir)
                    else:
                        raise

                p = Project(builddir=builddir, status="empty_project",
                            owner_id=owner_id)
                s.add(p)
        except BaseException:
            # If we have created a project directory but could not add the
            # project to the database, remove the otherwise orphaned directory
            # again.
            if directory_created:
                rmtree(builddir)  # OSError
            raise

    def del_project(self, builddir):
        # Throws: ElbeDBError, OSError
        p = None
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "cannot delete project %s while it is busy" %
                    builddir)

            if os.path.exists(builddir):
                # delete project in background to avoid blocking caller for a
                # long time if the project is huge
                t = Thread(target=rmtree, args=[builddir])
                t.start()

            s.query(ProjectVersion).\
                filter(ProjectVersion.builddir == builddir).delete()

            s.query(ProjectFile).\
                filter(ProjectFile.builddir == builddir).delete()

            s.delete(p)

    def reset_project(self, builddir, clean):
        # Throws: ElbeDBError, OSError
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            sourcexmlpath = os.path.join(builddir, "source.xml")
            if os.path.exists(sourcexmlpath):
                p.status = "needs_build"
            else:
                p.status = "empty_project"

        if clean:
            targetpath = os.path.join(builddir, "target")
            if os.path.exists(targetpath):
                rmtree(targetpath)      # OSError

            chrootpath = os.path.join(builddir, "chroot")
            if os.path.exists(chrootpath):
                rmtree(chrootpath)      # OSError

    def save_project(self, ep):
        # TODO: Recover in case writing the XML file or commiting the
        # database entry fails
        project = None

        with session_scope(self.session) as s:
            try:
                project = s.query(Project).filter(
                    Project.builddir == ep.builddir).one()
            except NoResultFound:
                pass

            if not os.path.exists(ep.builddir):
                os.makedirs(ep.builddir)
            if not os.path.isfile(ep.builddir + "/source.xml") and ep.xml:
                ep.xml.xml.write(ep.builddir + "/source.xml")

            with open(ep.builddir + "/source.xml") as xml_file:
                xml_str = xml_file.read()
                if not project:
                    project = Project(name=ep.xml.text("project/name"),
                                      version=ep.xml.text("project/version"),
                                      builddir=ep.builddir,
                                      xml=xml_str)
                    s.add(project)
                else:
                    project.edit = datetime.utcnow()
                    project.version = ep.xml.text("project/version")
                    project.xml = xml_str

    def load_project(
            self,
            builddir,
            url_validation=ValidationMode.CHECK_ALL):

        # pass exceptions if hook-scripts can't be loaded (they're optional)
        postbuild_file = None
        try:
            postbuild = self.get_project_file(builddir, 'postbuild.sh')
            postbuild_file = postbuild.builddir + '/' + postbuild.name
        except ElbeDBError:
            pass

        presh_file = None
        try:
            presh_handle = self.get_project_file(builddir, 'pre.sh')
            presh_file = presh_handle.builddir + '/' + presh_handle.name
        except ElbeDBError:
            pass

        postsh_file = None
        try:
            postsh_handle = self.get_project_file(builddir, 'post.sh')
            postsh_file = postsh_handle.builddir + '/' + postsh_handle.name
        except ElbeDBError:
            pass

        savesh_file = None
        try:
            savesh_handle = self.get_project_file(builddir, 'save.sh')
            savesh_file = savesh_handle.builddir + '/' + savesh_handle.name
        except ElbeDBError:
            pass

        with session_scope(self.session) as s:
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()

                return ElbeProject(p.builddir, name=p.name,
                                   postbuild_file=postbuild_file,
                                   presh_file=presh_file,
                                   postsh_file=postsh_file,
                                   savesh_file=savesh_file,
                                   url_validation=url_validation)
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

    def set_busy(self, builddir, allowed_status):
        assert "busy" not in allowed_status
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).with_lockmode('update'). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status not in allowed_status:
                raise ElbeDBError("project: " + builddir +
                                  " set_busy: invalid status: " + p.status)

            old_status = p.status
            p.status = "busy"
            return old_status

    def is_busy(self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir). \
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            return p.status == "busy"

    def reset_busy(self, builddir, new_status):
        assert new_status == "has_changes" or \
            new_status == "build_done" or \
            new_status == "build_failed"

        with session_scope(self.session) as s:
            try:
                p = s.query(Project).with_lockmode('update'). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status != "busy":
                raise ElbeDBError(
                    "project: " +
                    builddir +
                    " reset_busy: invalid status: " +
                    p.status)

            p.status = new_status

    def has_changes(self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir). \
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            return p.status == "has_changes"

    def get_owner_id(self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).\
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.owner_id is None:
                return None

            return int(p.owner_id)

    def set_project_version(self, builddir, new_version=None):
        if new_version == "":
            raise ElbeDBError("version number must not be empty")

        if not re.match("^[A-Za-z0-9_.-]{1,25}$", new_version):
            raise ElbeDBError(
                "version number must contain valid characters [A-Za-z0-9_-.]")

        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).\
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "empty_project" or p.status == "busy":
                raise ElbeDBError(
                    "project: " +
                    builddir +
                    " set_project_version: invalid status: " +
                    p.status)

            xmlpath = os.path.join(builddir, "source.xml")
            xml = ElbeXML(xmlpath, url_validation=ValidationMode.NO_CHECK)

            if new_version is not None:
                xml.node("/project/version").set_text(new_version)
                xml.xml.write(xmlpath)

            p.version = xml.text("/project/version")

    def list_project_versions(self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).\
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            return [ProjectVersionData(v) for v in p.versions]

    def save_version(self, builddir, description=None):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).\
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            assert p.status == "busy"

            sourcexmlpath = os.path.join(builddir, "source.xml")
            sourcexml = ElbeXML(sourcexmlpath,
                                url_validation=ValidationMode.NO_CHECK)

            version = sourcexml.text("project/version")
            if s.query(ProjectVersion).\
                    filter(ProjectVersion.builddir == builddir).\
                    filter(ProjectVersion.version == version).count() > 0:
                raise ElbeDBError(
                    "Version %s already exists for project in %s, "
                    "please change version number first" %
                    (version, builddir)
                )

            versionxmlname = get_versioned_filename(p.name, version,
                                                    ".version.xml")
            versionxmlpath = os.path.join(builddir, versionxmlname)
            copyfile(sourcexmlpath, versionxmlpath)

            v = ProjectVersion(builddir=builddir,
                               version=version,
                               description=description)
            s.add(v)

            _update_project_file(s, builddir, versionxmlname,
                                      "application/xml",
                                      "source.xml for version %s" % version)

    def set_version_description(self, builddir, version, description):
        with session_scope(self.session) as s:
            try:
                v = s.query(ProjectVersion).\
                    filter(ProjectVersion.builddir == builddir).\
                    filter(ProjectVersion.version == version).one()
            except NoResultFound:
                raise ElbeDBError(
                    "no such project version: %s (version %s)" %
                    (builddir, version))

            v.description = description

    def checkout_version_xml(self, builddir, version):
        with session_scope(self.session) as s:
            try:
                v = s.query(ProjectVersion).\
                    filter(ProjectVersion.builddir == builddir).\
                    filter(ProjectVersion.version == version).one()
            except NoResultFound:
                raise ElbeDBError(
                    "no such project version: %s (version %s)" %
                    (builddir, version))

            assert v.project.status == "busy"

            sourcexmlpath = os.path.join(builddir, "source.xml")
            versionxmlname = get_versioned_filename(v.project.name, version,
                                                    ".version.xml")
            versionxmlpath = os.path.join(builddir, versionxmlname)

            copyfile(versionxmlpath, sourcexmlpath)
            v.project.version = version

    def del_version(self, builddir, version, force=False):
        with session_scope(self.session) as s:
            try:
                v = s.query(ProjectVersion).\
                    filter(ProjectVersion.builddir == builddir).\
                    filter(ProjectVersion.version == version).one()
            except NoResultFound:
                raise ElbeDBError(
                    "no such project version: %s (version %s)" %
                    (builddir, version))

            if not force:
                if v.project.status == "busy":
                    raise ElbeDBError(
                        "cannot delete version of project in %s while "
                        "it is busy" % builddir)

            xmlname = get_versioned_filename(v.project.name, version,
                                             ".version.xml")
            xmlpath = os.path.join(builddir, xmlname)
            os.remove(xmlpath)
            s.delete(v)

            s.query(ProjectFile).filter(ProjectFile.builddir == builddir).\
                filter(ProjectFile.name == xmlname).delete()

    def get_version_xml(self, builddir, version):
        with session_scope(self.session) as s:
            try:
                v = s.query(ProjectVersion).\
                    filter(ProjectVersion.builddir == builddir).\
                    filter(ProjectVersion.version == version).one()
            except NoResultFound:
                raise ElbeDBError("no such project version: %s (version %s)" %
                                  (builddir, version))

            xmlname = get_versioned_filename(v.project.name, version,
                                             ".version.xml")
            return os.path.join(builddir, xmlname)

    def get_project_files(self, builddir):
        # Can throw: ElbeDBError
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "project: " +
                    builddir +
                    " get_project_files: invalid status: " +
                    p.status)

            return [ProjectFileData(f) for f in p.files]

    def get_project_file(self, builddir, name):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            if p.status == "busy":
                raise ElbeDBError(
                    "project: " +
                    builddir +
                    " get_project_file: invalid status: " +
                    p.status)

            try:
                f = s.query(ProjectFile).\
                    filter(ProjectFile.builddir == builddir).\
                    filter(ProjectFile.name == name).one()
            except NoResultFound:
                raise ElbeDBError(
                    "no file %s in project %s registered" %
                    (name, builddir))

            return ProjectFileData(f)

    def add_project_file(self, builddir, name, mime_type, description=None):
        with session_scope(self.session) as s:
            try:
                s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    builddir)

            _update_project_file(s, builddir, name, mime_type,
                                      description)

    def update_project_files(self, ep):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).\
                    filter(Project.builddir == ep.builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    "project %s is not registered in the database" %
                    ep.builddir)

            # Delete no longer existing files from the database
            files = s.query(ProjectFile).\
                filter(ProjectFile.builddir == ep.builddir).all()
            for f in files:
                if not os.path.isfile(os.path.join(ep.builddir, f.name)):
                    s.delete(f)

            # Add images from the given ElbeProject
            if ep.targetfs:

                images = set(ep.targetfs.images or [])
                for img in images:
                    _update_project_file(
                        s, p.builddir, img,
                        "application/octet-stream", "Image")

            # Add other generated files
            _update_project_file(s, p.builddir, "source.xml",
                                      "application/xml",
                                      "Current source.xml of the project")

            for name in ["chroot", "target", "sysroot-target", "sysroot-host"]:

                _update_project_file(s, p.builddir, "licence-%s.txt" % name,
                                     "text/plain; charset=utf-8",
                                     "License file")

                _update_project_file(s, p.builddir, "licence-%s.xml" % name,
                                     "application/xml",
                                     "xml License file")

            _update_project_file(s, p.builddir, "validation.txt",
                                      "text/plain; charset=utf-8",
                                      "Package list validation result")

            _update_project_file(s, p.builddir, "elbe-report.txt",
                                      "text/plain; charset=utf-8",
                                      "Report")

            _update_project_file(s, p.builddir, "log.txt",
                                      "text/plain; charset=utf-8",
                                      "Log file")

            _update_project_file(s, p.builddir, "sysroot.tar.xz",
                                      "application/x-xz-compressed-tar",
                                      "sysroot for cross-toolchains")

            sdk = glob.glob(os.path.join(p.builddir, "setup-elbe-sdk-*.sh"))
            try:
                # throws index error if no  setup-elbe-sdk-* file exists
                # that's ok because it might not yet been built
                sdkname = sdk[0].split('/')[-1]

                _update_project_file(s, p.builddir, sdkname,
                                        "application/x-shellscript",
                                        "SDK Installer")
            except IndexError:
                pass

            _update_project_file(s, p.builddir, "chroot.tar.xz",
                                      "application/x-xz-compressed-tar",
                                      "chroot for 'native' development")

            # Add Repository iso images
            for img in ep.repo_images:
                name = os.path.basename(img)
                _update_project_file(s, p.builddir, name,
                                          "application/octet-stream",
                                          "Repository IsoImage")

            # Scan pbuilder/build directory if that exists
            if os.path.exists(os.path.join(p.builddir, "pbuilder", "result")):
                pbresult_path = os.path.join(p.builddir, "pbuilder", "result")
                pfile_path = os.path.join("pbuilder", "result")
            else:
                pbresult_path = os.path.join(p.builddir, "pbuilder_cross",
                                             "result")
                pfile_path = os.path.join("pbuilder_cross", "result")

            if os.path.isdir(pbresult_path):
                for f in os.listdir(pbresult_path):
                    pfile = os.path.join(pfile_path, f)
                    _update_project_file(s, p.builddir, pfile,
                                              "application/octet-stream",
                                              "Pbuilder artifact")


    def add_user(self, name, fullname, password, email, admin):

        # pylint: disable=too-many-arguments

        # encrypt is deprecated but hash is not available in jessie
        try:
            pwhash = pbkdf2_sha512.hash(password)
        except AttributeError:
            pwhash = pbkdf2_sha512.encrypt(password)

        u = User(name=name,
                 fullname=fullname,
                 pwhash=pwhash,
                 email=email,
                 admin=admin)

        with session_scope(self.session) as s:
            if s.query(User).filter(User.name == name).count() > 0:
                raise ElbeDBError("user %s already exists in the database" %
                                  name)
            s.add(u)

    def modify_user(self, userid, name, fullname, email, admin,
                    password=None):

        # pylint: disable=too-many-arguments

        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            # If a user name change is requested, check for uniqueness
            if name != u.name:
                if s.query(User).filter(User.name == name).count() > 0:
                    raise ElbeDBError(
                        "user %s already exists in the database" % name)

            u.name = name
            u.fullname = fullname
            u.email = email
            u.admin = admin

            # Update password only if given
            if password is not None:
                # encrypt is deprecated but hash is not available in jessie
                try:
                    u.pwhash = pbkdf2_sha512.hash(password)
                except AttributeError:
                    u.pwhash = pbkdf2_sha512.encrypt(password)

    def del_user(self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            # Get a list of all projects owned by the user to delete. Set their
            # owner to nobody and return them to the caller later, so it can
            # decide whether to keep the projects or delete them.
            orphaned_projects = s.query(Project).\
                filter(Project.owner_id == userid).all()
            projectlist = []
            for p in orphaned_projects:
                p.owner_id = None
                projectlist.append(ProjectData(p))

            # Now delete the user and return the list
            s.delete(u)
            return projectlist

    def validate_login(self, name, password):
        with session_scope(self.session) as s:
            # Find the user with the given name
            try:
                u = s.query(User).filter(User.name == name).one()
            except NoResultFound:
                raise InvalidLogin()

            # Check password, throw an exception if invalid
            if not pbkdf2_sha512.verify(password, u.pwhash):
                raise InvalidLogin()

            # Everything good, now return the user id to the caller
            return int(u.id)

    def is_admin(self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            return bool(u.admin)

    def get_username(self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            return str(u.name)

    def get_user_data(self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            return UserData(u)

    def get_user_id(self, name):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.name == name).one()
            except NoResultFound:
                raise ElbeDBError("no user with name %s" % name)

            return int(u.id)

    @classmethod
    def init_db(cls, name, fullname, password, email, admin):

        # pylint: disable=too-many-arguments

        if not os.path.exists(cls.db_path):
            try:
                os.makedirs(cls.db_path)
            except OSError as e:
                print(str(e))
                return

        db = ElbeDB()

        try:
            db.add_user(name, fullname, password, email, admin)
        except ElbeDBError as e:
            print(str(e))


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, Sequence('article_aid_seq', start=1001, increment=1),
                primary_key=True)

    name = Column(String, unique=True)
    fullname = Column(String)
    pwhash = Column(String)
    email = Column(String)
    admin = Column(Boolean)
    projects = relationship("Project", backref="owner")


class UserData (object):
    def __init__(self, user):
        self.id = int(user.id)
        self.name = str(user.name)
        self.fullname = str(user.fullname)
        self.email = str(user.email)
        self.admin = bool(user.admin)


class Project (Base):
    __tablename__ = 'projects'

    builddir = Column(String, primary_key=True)
    name = Column(String)
    version = Column(String)
    xml = Column(String)
    status = Column(String)
    edit = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey('users.id'))
    versions = relationship("ProjectVersion", backref="project")
    files = relationship("ProjectFile", backref="project")


class ProjectData (object):
    def __init__(self, project):
        self.builddir = str(project.builddir)
        self.name = str(project.name)
        self.version = str(project.version)
        # self.xml        = str(project.xml) # omit, as long as not needed
        self.status = str(project.status)
        self.edit = datetime(project.edit.year, project.edit.month,
                             project.edit.day, project.edit.hour,
                             project.edit.minute, project.edit.second,
                             project.edit.microsecond, project.edit.tzinfo)


class ProjectVersion (Base):
    __tablename__ = 'projectversions'

    builddir = Column(String, ForeignKey('projects.builddir'),
                      primary_key=True)
    version = Column(String, primary_key=True)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ProjectVersionData (object):
    def __init__(self, pv):
        self.builddir = str(pv.builddir)
        self.version = str(pv.version)
        if pv.description:
            self.description = str(pv.description)
        else:
            self.description = None
        self.timestamp = datetime(
            pv.timestamp.year,
            pv.timestamp.month,
            pv.timestamp.day,
            pv.timestamp.hour,
            pv.timestamp.minute,
            pv.timestamp.second,
            pv.timestamp.microsecond,
            pv.timestamp.tzinfo)


class ProjectFile (Base):
    __tablename__ = 'files'

    name = Column(String, primary_key=True)
    builddir = Column(String, ForeignKey('projects.builddir'),
                      primary_key=True)
    mime_type = Column(String, nullable=False)
    description = Column(String)


class ProjectFileData (object):
    def __init__(self, pf):
        self.name = str(pf.name)
        self.builddir = str(pf.builddir)
        self.mime_type = str(pf.mime_type)
        if pf.description:
            self.description = str(pf.description)
        else:
            self.description = None
