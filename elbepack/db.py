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
from shutil import (rmtree, copyfile)
from contextlib import contextmanager

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

class ElbeDB(object):
    db_path     = '/var/cache/elbe'
    db_location = 'sqlite:///' + db_path + '/elbe.db'
    
    def __init__ (self):
        engine = create_engine( self.__class__.db_location )
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

    def get_files (self, builddir):
        # Can throw: ElbeDBError, IOError

        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

        with session_scope(self.session) as s:
            try:
                p = s.query (Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status != "build_done":
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            files = []

            with open (builddir+"/files-to-extract") as fte:    #IOError
                files.append (fte.read ())      #IOError

        return files

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

            if p.status == "build_in_progress":
                raise ElbeDBError(
                        "cannot set XML file while project %s is being built" %
                        builddir )

            xml = ElbeXML (xml_file)    #ValidationError

            p.name = xml.text ("project/name")
            p.version = xml.text ("project/version")
            p.edit = datetime.utcnow ()
            p.status = "needs_build"

            copyfile (xml_file, builddir+"/source.xml");    #OSError


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

            if p.status == "build_in_progress":
                raise ElbeDBError(
                        "cannot delete project %s while it is being built" %
                        builddir )

            if os.path.exists (builddir):
                rmtree (builddir)   # OSError

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


    def set_build_in_progress (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).with_lockmode( 'update' ). \
                        filter( Project.builddir == builddir ).one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "build_in_progress" or p.status == "empty_project":
                raise ElbeDBError( "project: " + builddir +
                        " invalid status: " + p.status )

            p.status = "build_in_progress"


    def is_build_in_progress (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).filter( Project.builddir == builddir ). \
                        one()
            except NoResultFound:
                raise ElbeDBError(
                        "project %s is not registered in the database" %
                        builddir )

            if p.status == "build_in_progress":
                return True
            else:
                return False


    def set_build_done (self, builddir, successful=True):
        with session_scope(self.session) as s:
            try:
                p = s.query( Project ).with_lockmode( 'update' ). \
                        filter( Project.builddir == builddir ).one()
            except NoResultFound:
                raise ElbeDBError( "project %s is not registered in the database" %
                        builddir )

            if p.status != "build_in_progress":
                raise ElbeDBError( "project: " + builddir + " invalid status: " +
                        p.status )

            if successful:
                p.status = "build_done"
            else:
                p.status = "build_failed"


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
