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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, Boolean, Sequence, DateTime)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from elbepack.elbeproject import ElbeProject

db_path     = '/var/cache/elbe'
db_location = 'sqlite:///' + db_path + '/elbe.db'

Base = declarative_base ()

def get_db_session ():
    if not os.path.exists (db_path)
        os.makedirs (db_path)
    engine = create_engine (db_location)
    Base.metadata.create_all (engine)
    Session = sessionmaker (bind=engine)
    return Session ()

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

    @classmethod
    def get_userid(self, user_name):
        user = DBSession.query(User).filter(User.name == user_name).first()
        return user.id

    @classmethod
    def verify_password(self, name, password):
        passwd = DBSession.query(User.password).\
                            filter(User.name == name).first()
        if passwd != None:
            return passwd[0] == password
        else:
            print "No user found "

    @classmethod
    def get_user_role(self, name):
        role = DBSession.query(User.password).filter(User.name == name).first()
        print role
        if role != None:
            return role[0] == True
        else:
            print "No role ? Wrong db entry ?"

    @classmethod
    def user_in_db(self, name):
        in_db = DBSession.query(User).filter(User.name == name).first()
        return in_db

class Project (Base):
    __tablename__ = 'projects'

    builddir = Column (String, primary_key=True)
    name     = Column (String)
    version  = Column (String)
    xml      = Column (String)
    edit     = Column (DateTime, default=datetime.utcnow)

def save_project (ep):
    session = get_db_session ()

    project = None

    try:
        project = session.query (Project).filter (
                    Project.builddir == ep.builddir).one ()
    except NoResultFound:
        pass

    with open (ep.builddir + "/source.xml") as xml_file:
        xml_str  = xml_file.read ()
        if not project:
            project = Project (name = ep.xml.text ("project/name"),
                               version = ep.xml.text ("project/version"),
                               builddir = ep.builddir,
                               xml = xml_str)
            session.add (project)
        else:
            project.edit = datetime.utcnow ()
            project.version = ep.xml.text ("project/version")
            project.xml = xml_str

    session.commit ()

def load_project (builddir):
    session = get_db_session ()
    try:
        p = session.query(Project).filter(Project.builddir == builddir).one()
        return ElbeProject (p.builddir, name=p.name)
    except NoResultFound:
        return None
