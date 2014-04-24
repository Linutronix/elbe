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

from datetime import datetime
from shutil import (rmtree, copyfile)
from contextlib import contextmanager

from passlib.hash import pbkdf2_sha512

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, Boolean, Sequence, DateTime)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
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

class LoginData(object):
    def __init__(self, userid, admin):
        self.userid = userid
        self.admin = admin

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
            return s.query (User)

    def list_projects (self):
        with session_scope(self.session) as s:
            return s.query (Project)

    def get_files (self, builddir):
        # Can throw: ElbeDBError, IOError

        if not os.path.exists (builddir):
            raise ElbeDBError( "project directory does not exist" )

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

            xml = ElbeXML (xml_file)    #ValidationError

            p.name = xml.text ("project/name")
            p.version = xml.text ("project/version")
            p.edit = datetime.utcnow ()
            p.status = "needs_build"

            copyfile (xml_file, builddir+"/source.xml");    #OSError


    # TODO what about source.xml ? stored always in db ? version management ?
    #       build/need_rebuild state ? locking ?

    def create_project (self, builddir):
        # Throws: ElbeDBError, OSError
        if os.path.exists (builddir):
            raise ElbeDBError( "project directory %s already exists" %
                    builddir )

        os.makedirs (builddir)  #OSError

        p = Project (builddir=builddir, status="empty_project")

        try:
            with session_scope(self.session) as s:
                s.add (p)
        except ElbeDBError as e:
            # If we fail to create the database entry, we have to remove the
            # fresh and otherwise orphaned build directory.
            rmtree (builddir)
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
                p.status = "needs_rebuild"
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


    def load_project (self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project). \
                        filter(Project.builddir == builddir).one()
                return ElbeProject (p.builddir, name=p.name)
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


    ### User management ###

    def add_user (self, name, fullname, password, email, admin):
        u = User( name = name,
                  fullname = fullname,
                  pwhash = pbkdf2_sha512.encrypt( password ),
                  email = email,
                  admin = admin )
        with session_scope(self.session) as s:
            s.add( u )

    def get_logindata (self, name, password):
        with session_scope(self.session) as s:
            # Find the user with the given name
            try:
                u = s.query(User).filter(User.name == name).one()
            except NoResultFound:
                raise InvalidLogin()

            # Check password, throw an exception if invalid
            if not pbkdf2_sha512.verify( password, u.pwhash ):
                raise InvalidLogin()

            # Everything good, now return the user id and the role to
            # the caller
            return LoginData( userid=u.id, admin=u.admin )


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
    # projects = relationship("Project", backref="users")


class Project (Base):
    __tablename__ = 'projects'

    builddir = Column (String, primary_key=True)
    name     = Column (String)
    version  = Column (String)
    xml      = Column (String)
    status   = Column (String)
    edit     = Column (DateTime, default=datetime.utcnow)
