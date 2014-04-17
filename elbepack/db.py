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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, Boolean, Sequence, DateTime)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import (ElbeXML, ValidationError)

Base = declarative_base ()

class ElbeDB(object):
    db_path     = '/var/cache/elbe'
    db_location = 'sqlite:///' + db_path + '/elbe.db'
    
    def __init__ (self):
        engine = create_engine( self.__class__.db_location )
        Base.metadata.create_all( engine )
        smaker = sessionmaker( bind=engine )
        self.session = smaker()

    def list_users (self):
        return self.session.query (User)

    def list_projects (self):
        return self.session.query (Project)

    def get_files (self, builddir):
        if not os.path.exists (builddir):
            print "project directory doesn't exist"
            return

        files = []
        try:
            with open (builddir+"/files-to-extract") as fte:
                files.append (fte.read ())
        except IOError as e:
            print e
            return None

        return files

    def set_xml (self, builddir, xml_file):
        if not os.path.exists (builddir):
            print "project directory doesn't exist"
            return

        p = None
        try:
            p = self.session.query (Project). \
                    filter(Project.builddir == builddir).one()
        except NoResultFound:
            print "project:", builddir, "isn't in db"
            return

        try:
            xml = ElbeXML (xml_file)
        except ValidationError as e:
            print e
            return

        p.name = xml.text ("project/name")
        p.version = xml.text ("project/version")
        p.edit = datetime.utcnow ()
        p.status = "needs_build"

        try:
            copyfile (xml_file, builddir+"/source.xml");
        except OSError as e:
            print "copy xml_file to builddir failed", e
            return

        try:
            self.session.commit ()
        except OperationalError as e:
            print e
            return


    # TODO what about source.xml ? stored always in db ? version management ?
    #       build/need_rebuild state ? locking ?

    def create_project (self, builddir):
        if os.path.exists (builddir):
            print "project directory already exists"
            return

        try:
            os.makedirs (builddir)
        except OSError as e:
            print "create build directory failed", e
            return

        p = Project (builddir=builddir, status="empty_project")

        self.session.add (p)
        try:
            self.session.commit ()
        except OperationalError as e:
            print e
            return


    def del_project (self, builddir):
        p = None
        try:
            p = self.session.query (Project).filter(Project.builddir == builddir).one()
        except NoResultFound:
            print "project:", builddir, "isn't in db"
            return

        self.session.delete (p)

        if not os.path.exists (builddir):
            print "project directory doesn't exist"
            return

        try:
            rmtree (builddir)
        except OSError as e:
            print "remove build directory failed", e
            return

        try:
            self.session.commit ()
        except OperationalError as e:
            print e
            return

    def save_project (self, ep):
        project = None

        try:
            project = self.session.query (Project).filter (
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
                self.session.add (project)
            else:
                project.edit = datetime.utcnow ()
                project.version = ep.xml.text ("project/version")
                project.xml = xml_str

        self.session.commit ()


    def load_project (self, builddir):
        try:
            p = self.session.query(Project). \
                    filter(Project.builddir == builddir).one()
            return ElbeProject (p.builddir, name=p.name)
        except NoResultFound:
            return None


    def build_project (self, builddir):
        if not os.path.exists (builddir):
            print "project directory doesn't exist"
            return

        p = None
        try:
            p = self.session.query (Project). \
                    filter(Project.builddir == builddir).one()
        except NoResultFound:
            print "project:", builddir, "isn't in db"
            return

        if p.status == "build_in_progress":
            print "project:", builddir, "invalid status:", p.status
            return

        if p.status == "empty_project":
            print "project:", builddir, "invalid status:", p.status
            return

        p.status = "build_in_progress"
        self.session.commit ()

        # TODO progress notifications
        ep = self.load_project (builddir)
        ep.build (skip_debootstrap = True)

        p.status = "build_done"
        self.session.commit ()

    ### User management ###

    def add_user (self, name, fullname, password, email, admin):
        # TODO store a hash instead of plaintext
        u = User( name = name,
                  fullname = fullname,
                  password = password,
                  email = email,
                  admin = admin )
        self.session.add( u )
        self.session.commit()

    def get_userid (self, user_name):
        id = self.session.query(User.id).filter(User.name == user_name).first()
        return id

    def verify_password (self, name, password):
        stored_password = self.session.query(User.password).\
                filter(User.name == name).first()
        if stored_password is None:
            # For a non-existent user, password verification always fails
            return False
        else:
            # TODO compare hashes instead of plaintext
            return stored_password == password

    def get_user_role (self, name):
        role = self.session.query(User.admin).\
                filter(User.name == name).first()
        return role

    @classmethod
    def init_db (cls, name, fullname, password, email, admin):
        if not os.path.exists (cls.db_path):
            try:
                os.makedirs (db_path)
            except OSError as e:
                print e
                return

        db = ElbeDB()

        try:
            db.add_user(name, fullname, password, email, admin)
        except OperationalError as e:
            print e
            return


class User(Base):
    __tablename__ = 'users'

    id = Column (Integer, Sequence('article_aid_seq', start=1001, increment=1),
                 primary_key=True)

    name     = Column (String)
    fullname = Column (String)
    password = Column (String)
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
