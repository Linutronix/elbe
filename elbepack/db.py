#!/usr/bin/env python
#
# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import errno

from datetime import datetime
from shutil import (rmtree, copyfile, copyfileobj)
from contextlib import contextmanager
from urllib import quote

from passlib.hash import pbkdf2_sha512

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, ForeignKey)
from sqlalchemy import (Integer, String, Boolean, Sequence, DateTime)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, object_mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import (ElbeXML, ValidationError)

Base = declarative_base ()

class ElbeDBError(Exception):
    def __init__ (self, message):
        Exception.__init__(self, message)

class InvalidLogin(Exception):
    def __init__ (self):
        Exception.__init__(self, "Invalid login")

@contextmanager
def session_scope(session):
    try:
        yield session
        try:
            session.commit()
        except OperationalError as e:
            raise ElbeDBError( "database commit failed: " + str(e) )
    except:
        session.rollback()
        raise
    finally:
        session.remove()

def get_versioned_filename( name, version, suffix ):
    return quote( name, ' ') + '_' + quote( version, ' ') + suffix

class ElbeDB(object):
    db_path     = '/var/cache/elbe'
    db_location = 'sqlite:///' + db_path + '/elbe.db'

    def __init__ (self):
        engine = create_engine( self.__class__.db_location,
                connect_args={ 'timeout': 30 } )
        Base.metadata.create_all( engine )
        smaker = sessionmaker( bind=engine )
        self.session = scoped_session( smaker )

    def list_users (self):
        with session_scope(self.session) as s:
            res = s.query (User).all()
            ret = []
            for u in res:
                ret.append(UserData(u))
            return ret

    def list_projects (self):
        with session_scope(self.session) as s:
            res = s.query (Project).all()
            ret = []
            for p in res:
                ret.append(ProjectData(p))
            return ret

    def list_projects_of (self, userid):
        with session_scope(self.session) as s:
            res = s.query (Project).filter (Project.owner_id == userid).all()
            ret = []
            for p in res:
                ret.append(ProjectData(p))
            return ret

    def get_project_data (self, builddir):
        # Can throw: ElbeDBError
        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            return ProjectData(p)

    def set_presh (self, builddir, presh_file):
        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query (Project). \
                        filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError(
                        "cannot set presh file while project %s is busy" %
                        builddir )

            p.edit = datetime.utcnow ()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            with open (builddir+"/"+p.version+"-pre.sh", 'w') as dst:
                copyfileobj (presh_file, dst)

            self._update_project_file( s, builddir, p.version+"-pre.sh",
                    "application/sh", "pre install script" )

    def set_postsh (self, builddir, postsh_file):
        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query (Project). \
                        filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError(
                        "cannot set postsh file while project %s is busy" %
                        builddir )

            p.edit = datetime.utcnow ()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            with open (builddir+"/"+p.version+"-pre.sh", 'w') as dst:
                copyfileobj (postsh_file, dst)

            self._update_project_file( s, builddir, p.version+"-pre.sh",
                    "application/sh", "pre install script" )


    def set_xml (self, builddir, xml_file):
        # This method can throw: ElbeDBError, ValidationError, OSError

        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query (Project). \
                        filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError(
                        "cannot set XML file while project %s is busy" %
                        builddir )

            xml = ElbeXML (xml_file)    #ValidationError

            p.name = xml.text ("project/name")
            p.version = xml.text ("project/version")
            p.edit = datetime.utcnow ()
            if p.status == "empty_project" or p.status == "build_failed":
                p.status = "needs_build"
            elif p.status == "build_done":
                p.status = "has_changes"

            copyfile (xml_file, builddir+"/source.xml");    #OSError
            self._update_project_file( s, builddir, "source.xml",
                    "application/xml", "ELBE recipe of the project" )


    # TODO what about source.xml ? stored always in db ? version management ?
    #       build/needs_build state ? locking ?

    def create_project (self, builddir, owner_id = None):
        # Throws: ElbeDBError, OSError
        directory_created = False

        try:
            with session_scope(self.session) as s:
                if s.query(Project).\
                        filter(Project.builddir == builddir).count() > 0:
                    raise ElbeDBError( "project %s already exists in database" %
                            builddir )

                try:
                    os.makedirs (builddir)  #OSError
                    directory_created = True
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        raise ElbeDBError(
                                "project directory %s already exists" %
                                builddir )
                    else:
                        raise

                p = Project (builddir=builddir, status="empty_project",
                        owner_id=owner_id)
                s.add (p)
        except:
            # If we have created a project directory but could not add the
            # project to the database, remove the otherwise orphaned directory
            # again.
            if directory_created:
                rmtree (builddir)       #OSError
            raise


    def del_project (self, builddir):
        # Throws: ElbeDBError, OSError
        p = None
        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError(
                        "cannot delete project %s while it is busy" %
                        builddir )

            if os.path.exists (builddir):
                rmtree (builddir)   # OSError

            s.query( ProjectVersion ).\
                    filter( ProjectVersion.builddir == builddir ).delete()

            s.query( ProjectFile ).\
                    filter( ProjectFile.builddir == builddir ).delete()

            s.delete (p)


    def reset_project (self, builddir, clean):
        # Throws: ElbeDBError, OSError
        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            sourcexmlpath = os.path.join( builddir, "source.xml" )
            if os.path.exists( sourcexmlpath ):
                p.status = "needs_build"
            else:
                p.status = "empty_project"

        if clean:
            targetpath = os.path.join( builddir, "target" )
            if os.path.exists( targetpath ):
                rmtree( targetpath )      # OSError

            chrootpath = os.path.join( builddir, "chroot" )
            if os.path.exists( chrootpath ):
                rmtree( chrootpath )      # OSError


    def save_project (self, ep):
        # TODO: Recover in case writing the XML file or commiting the
        # database entry fails
        project = None

        with session_scope(self.session) as s:
            try:
                project = s.query (Project).filter (
                            Project.builddir == ep.builddir).one ()
            except NoResultFound:
                pass

            if not os.path.exists (ep.builddir):
                os.makedirs (ep.builddir)
            if not os.path.isfile (ep.builddir + "/source.xml") and ep.xml:
                ep.xml.xml.write (ep.builddir + "/source.xml")

            with open (ep.builddir + "/source.xml") as xml_file:
                xml_str  = xml_file.read ()
                if not project:
                    project = Project (name = ep.xml.text ("project/name"),
                                       version = ep.xml.text ("project/version"),
                                       builddir = ep.builddir,
                                       xml = xml_str)
                    s.add (project)
                else:
                    project.edit = datetime.utcnow ()
                    project.version = ep.xml.text ("project/version")
                    project.xml = xml_str


    def load_project (self, builddir, logpath = None):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project). \
                        filter(Project.builddir == builddir).one()
                return ElbeProject (p.builddir, name=p.name, logpath=logpath)
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )


    def set_busy (self, builddir, allowed_status):
        assert not "busy" in allowed_status
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).with_lockmode( 'update' ). \
                        filter( Project.builddir == builddir ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if not p.status in allowed_status:
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            old_status = p.status
            p.status = "busy"
            return old_status


    def is_busy (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir ). \
                        one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                return True
            else:
                return False


    def reset_busy (self, builddir, new_status):
        assert new_status == "has_changes" or \
               new_status == "build_done" or \
               new_status == "build_failed"

        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).with_lockmode( 'update' ). \
                        filter( Project.builddir == builddir ).one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            if p.status != "busy":
                raise ElbeDBError( "project: " + builddir + " invalid status: " +
                        p.status )

            p.status = new_status


    def has_changes (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir ). \
                        one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "has_changes":
                return True
            else:
                return False


    def get_owner_id (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir ).\
                        one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            if p.owner_id is None:
                return None
            else:
                return int(p.owner_id)


    def set_project_version( self, builddir, new_version = None):
        if new_version == "":
            raise ElbeDBError( "version number must not be empty" )

        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir ).\
                        one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            if p.status == "empty_project" or p.status == "busy":
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            xmlpath = os.path.join( builddir, "source.xml" )
            xml = ElbeXML( xmlpath )

            if not new_version is None:
                xml.node( "/project/version" ).set_text( new_version )
                xml.xml.write( xmlpath )

            p.version = xml.text( "/project/version" )


    ### Version management ###

    def list_project_versions (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir).\
                        one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            return [ProjectVersionData(v) for v in p.versions]

    def save_version (self, builddir, description = None):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir).\
                        one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            assert p.status == "busy"

            sourcexmlpath = os.path.join( builddir, "source.xml" )
            sourcexml = ElbeXML( sourcexmlpath )

            version = sourcexml.text( "project/version" )
            if s.query( ProjectVersion ).\
                    filter( ProjectVersion.builddir == builddir ).\
                    filter( ProjectVersion.version == version ).count() > 0:
                raise ElbeDBError(
                        "Version %s already exists for project in %s, "
                        "please change version number first" %\
                                (version, builddir)
                        )

            versionxmlname = get_versioned_filename( p.name, version,
                    ".version.xml" )
            versionxmlpath = os.path.join( builddir, versionxmlname )
            copyfile( sourcexmlpath, versionxmlpath )

            v = ProjectVersion( builddir = builddir,
                                version = version,
                                description = description )
            s.add(v)

            self._update_project_file( s, builddir, versionxmlname,
                    "application/xml",
                    "source.xml for version %s" % version )

    def set_version_description (self, builddir, version, description):
        with session_scope(self.session) as s:
            try:
                v = s.query( ProjectVersion ).\
                        filter( ProjectVersion.builddir == builddir ).\
                        filter( ProjectVersion.version == version ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "no such project version: %s (version %s)" %
                        (builddir, version) )

            v.description = description

    def checkout_version_xml (self, builddir, version):
        with session_scope(self.session) as s:
            try:
                v = s.query( ProjectVersion ).\
                        filter( ProjectVersion.builddir == builddir ).\
                        filter( ProjectVersion.version == version ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "no such project version: %s (version %s)" %
                        (builddir, version) )

            assert v.project.status == "busy"

            sourcexmlpath = os.path.join( builddir, "source.xml" )
            versionxmlname = get_versioned_filename( v.project.name, version,
                    ".version.xml" )
            versionxmlpath = os.path.join( builddir, versionxmlname )

            copyfile( versionxmlpath, sourcexmlpath )
            v.project.version = version

    def del_version (self, builddir, version, force=False):
        with session_scope(self.session) as s:
            try:
                v = s.query( ProjectVersion ).\
                        filter( ProjectVersion.builddir == builddir ).\
                        filter( ProjectVersion.version == version ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "no such project version: %s (version %s)" %
                        (builddir, version) )

            if not force:
                if v.project.status == "busy":
                    raise ElbeDBError(
                            "cannot delete version of project in %s while "
                            "it is busy" % builddir )

            xmlname = get_versioned_filename( v.project.name, version,
                    ".version.xml" )
            xmlpath = os.path.join( builddir, xmlname )
            os.remove( xmlpath )
            s.delete( v )

            s.query( ProjectFile ).filter( ProjectFile.builddir == builddir ).\
                    filter( ProjectFile.name == xmlname ).delete()

    def get_version_xml (self, builddir, version):
        with session_scope(self.session) as s:
            try:
                v = s.query( ProjectVersion ).\
                        filter( ProjectVersion.builddir == builddir ).\
                        filter( ProjectVersion.version == version ).one()
            except NoResultFound:
                raise ElbeDBError( "no such project version: %s (version %s)" %
                        (builddir, version) )

            xmlname = get_versioned_filename( v.project.name, version,
                    ".version.xml" )
            return os.path.join( builddir, xmlname )


    ### File management ###

    def get_project_files (self, builddir):
        # Can throw: ElbeDBError
        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            return [ ProjectFileData(f) for f in p.files ]

    def get_project_file (self, builddir, name):
        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "busy":
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            try:
                f = s.query( ProjectFile ).\
                        filter( ProjectFile.builddir == builddir ).\
                        filter( ProjectFile.name == name ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "no file %s in project %s registered" %
                        ( name, builddir ) )

            return ProjectFileData(f)

    def add_project_file (self, builddir, name, mime_type, description = None):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir).\
                        one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            self._update_project_file( s, builddir, name, mime_type,
                    description )

    def update_project_files (self, ep):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).\
                        filter( Project.builddir == ep.builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            # Delete no longer existing files from the database
            files = s.query( ProjectFile ).\
                    filter( ProjectFile.builddir == ep.builddir ).all()
            for f in files:
                if not os.path.isfile( os.path.join( ep.builddir, f.name ) ):
                    s.delete( f )

            # Add images from the given ElbeProject
            if ep.targetfs:

                images = set( ep.targetfs.images or [] )
                for img in images:
                    self._update_project_file( s, p.builddir, img,
                            "application/octet-stream", "Image" )

            # Add other generated files
            self._update_project_file( s, p.builddir, "source.xml",
                    "application/xml", "Current source.xml of the project" )
            self._update_project_file( s, p.builddir, "license.txt",
                    "text/plain; charset=utf-8", "License file" )
            self._update_project_file( s, p.builddir, "validation.txt",
                    "text/plain; charset=utf-8", "Package list validation result" )
            self._update_project_file( s, p.builddir, "elbe-report.txt",
                    "text/plain; charset=utf-8", "Report" )
            self._update_project_file( s, p.builddir, "log.txt",
                    "text/plain; charset=utf-8", "Log file" )

    def _update_project_file (self, s, builddir, name, mime_type, description):
        try:
            f = s.query( ProjectFile ).\
                    filter( ProjectFile.builddir == builddir ).\
                    filter( ProjectFile.name == name).one()
        except NoResultFound:
            if os.path.isfile( os.path.join( builddir, name ) ):
                f = ProjectFile( builddir = builddir,
                        name = name,
                        mime_type = mime_type,
                        description = description )
                s.add( f )
            return

        if os.path.isfile( os.path.join( builddir, name ) ):
            f.mime_type = mime_type
            f.description = description
        else:
            s.delete( f )


    ### User management ###

    def add_user (self, name, fullname, password, email, admin):
        u = User( name = name,
                  fullname = fullname,
                  pwhash = pbkdf2_sha512.encrypt( password ),
                  email = email,
                  admin = admin )
        with session_scope(self.session) as s:
            if s.query(User).filter(User.name == name).count() > 0:
                raise ElbeDBError( "user %s already exists in the database"  %
                        name )
            s.add( u )

    def modify_user (self, userid, name, fullname, email, admin,
            password = None):
        with session_scope(self.session) as s:
            try:
                u = s.query( User ).filter( User.id == userid ).one()
            except NoResultFound:
                raise ElbeDBError( "no user with id %i" % userid )

            # If a user name change is requested, check for uniqueness
            if name != u.name:
                if s.query(User).filter(User.name == name).count() > 0:
                    raise ElbeDBError(
                            "user %s already exists in the database" % name )

            u.name = name
            u.fullname = fullname
            u.email = email
            u.admin = admin

            # Update password only if given
            if not password is None:
                u.pwhash = pbkdf2_sha512.encrypt( password )

    def del_user (self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query( User ).filter( User.id == userid ).one()
            except NoResultFound:
                raise ElbeDBError( "no user with id %i" % userid )

            # Get a list of all projects owned by the user to delete. Set their
            # owner to nobody and return them to the caller later, so it can
            # decide whether to keep the projects or delete them.
            orphaned_projects = s.query( Project ).\
                    filter( Project.owner_id == userid ).all()
            projectlist = []
            for p in orphaned_projects:
                p.owner_id = None
                projectlist.append( ProjectData(p) )

            # Now delete the user and return the list
            s.delete( u )
            return projectlist

    def validate_login (self, name, password):
        with session_scope(self.session) as s:
            # Find the user with the given name
            try:
                u = s.query(User).filter(User.name == name).one()
            except NoResultFound:
                raise InvalidLogin()

            # Check password, throw an exception if invalid
            if not pbkdf2_sha512.verify( password, u.pwhash ):
                raise InvalidLogin()

            # Everything good, now return the user id to the caller
            return int(u.id)

    def is_admin (self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError("no user with id %i" % userid)

            return bool(u.admin)

    def get_username (self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError( "no user with id %i" % userid)

            return str(u.name)

    def get_user_data (self, userid):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.id == userid).one()
            except NoResultFound:
                raise ElbeDBError( "no user with id %i" % userid)

            return UserData(u)

    def get_user_id (self, name):
        with session_scope(self.session) as s:
            try:
                u = s.query(User).filter(User.name == name).one()
            except NoResultFound:
                raise ElbeDBError( "no user with name %s" % name )

            return int(u.id)


    @classmethod
    def init_db (cls, name, fullname, password, email, admin):
        if not os.path.exists (cls.db_path):
            try:
                os.makedirs (cls.db_path)
            except OSError as e:
                print e
                return

        db = ElbeDB()

        try:
            db.add_user(name, fullname, password, email, admin)
        except ElbeDBError as e:
            print e


class User(Base):
    __tablename__ = 'users'

    id = Column (Integer, Sequence('article_aid_seq', start=1001, increment=1),
                 primary_key=True)

    name     = Column (String, unique=True)
    fullname = Column (String)
    pwhash   = Column (String)
    email    = Column (String)
    admin    = Column (Boolean)
    projects = relationship("Project", backref="owner")

class UserData (object):
    def __init__ (self, user):
        self.id         = int(user.id)
        self.name       = str(user.name)
        self.fullname   = str(user.fullname)
        self.email      = str(user.email)
        self.admin      = bool(user.admin)


class Project (Base):
    __tablename__ = 'projects'

    builddir = Column (String, primary_key=True)
    name     = Column (String)
    version  = Column (String)
    xml      = Column (String)
    status   = Column (String)
    edit     = Column (DateTime, default=datetime.utcnow)
    owner_id = Column (Integer, ForeignKey('users.id'))
    versions = relationship("ProjectVersion", backref="project")
    files    = relationship("ProjectFile", backref="project")

class ProjectData (object):
    def __init__ (self, project):
        self.builddir   = str(project.builddir)
        self.name       = str(project.name)
        self.version    = str(project.version)
        #self.xml        = str(project.xml) # omit, as long as not needed
        self.status     = str(project.status)
        self.edit       = datetime(project.edit.year, project.edit.month,
                            project.edit.day, project.edit.hour,
                            project.edit.minute, project.edit.second,
                            project.edit.microsecond, project.edit.tzinfo)


class ProjectVersion (Base):
    __tablename__ = 'projectversions'

    builddir        = Column (String, ForeignKey('projects.builddir'),
                              primary_key=True )
    version         = Column (String, primary_key=True)
    description     = Column (String)

class ProjectVersionData (object):
    def __init__ (self, pv):
        self.builddir       = str(pv.builddir)
        self.version        = str(pv.version)
        if pv.description:
            self.description    = str(pv.description)
        else:
            self.description    = None


class ProjectFile (Base):
    __tablename__ = 'files'

    name        = Column (String, primary_key=True)
    builddir    = Column (String, ForeignKey('projects.builddir'),
                          primary_key=True)
    mime_type   = Column (String, nullable=False)
    description = Column (String)

class ProjectFileData (object):
    def __init__ (self, pf):
        self.name           = str(pf.name)
        self.builddir       = str(pf.builddir)
        self.mime_type      = str(pf.mime_type)
        if pf.description:
            self.description    = str(pf.description)
        else:
            self.description    = None
