# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH


import errno
import glob
import os
import warnings
from contextlib import contextmanager
from datetime import datetime
from shutil import copyfile, rmtree
from threading import Thread

with warnings.catch_warnings():
    # passlib has code to handle absence of the crypt module and will work just
    # fine for our usecase without it.
    warnings.filterwarnings('ignore', "'crypt' is deprecated", DeprecationWarning)
    from passlib.hash import pbkdf2_sha512

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Sequence,
    String,
    create_engine,
)
from sqlalchemy.exc import OperationalError
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from elbepack.elbeproject import ElbeProject
from elbepack.elbexml import ElbeXML, ValidationMode


Base = declarative_base()


class ElbeDBError(Exception):
    pass


class InvalidLogin(Exception):
    def __init__(self):
        super().__init__('Invalid login')


@contextmanager
def session_scope(session):
    try:
        yield session
        try:
            session.commit()
        except OperationalError as e:
            raise ElbeDBError('database commit failed: ' + str(e))
    except BaseException:
        session.rollback()
        raise
    finally:
        session.remove()


def _update_project_file(s, builddir, name, mime_type, description):

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


class ElbeDB:

    db_path = '/var/cache/elbe'
    db_location = 'sqlite:///' + db_path + '/elbe.db'

    def __init__(self):
        engine = create_engine(self.__class__.db_location,
                               connect_args={'timeout': 60})
        Base.metadata.create_all(engine)
        smaker = sessionmaker(bind=engine)
        self.session = scoped_session(smaker)

    def list_projects(self):
        with session_scope(self.session) as s:
            res = s.query(Project).all()
            ret = []
            for p in res:
                ret.append(ProjectData(p))
            return ret

    def get_project_data(self, builddir):
        # Can throw: ElbeDBError
        if not os.path.exists(builddir):
            raise ElbeDBError('project directory does not exist')

        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            return ProjectData(p)

    def set_xml(self, builddir, xml_file):
        # This method can throw: ElbeDBError, ValidationError, OSError

        if not os.path.exists(builddir):
            raise ElbeDBError('project directory does not exist')

        srcxml_fname = os.path.join(builddir, 'source.xml')

        if xml_file is None:
            xml_file = srcxml_fname

        with session_scope(self.session) as s:
            p = None
            try:
                p = s.query(Project). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            if p.status == 'busy':
                raise ElbeDBError(
                    f'cannot set XML file while project {builddir} is busy')

            xml = ElbeXML(
                xml_file,
                url_validation=ValidationMode.NO_CHECK)  # ValidationError

            p.name = xml.text('project/name')
            p.version = xml.text('project/version')
            p.edit = datetime.utcnow()
            if p.status == 'empty_project' or p.status == 'build_failed':
                p.status = 'needs_build'
            elif p.status == 'build_done':
                p.status = 'has_changes'

            if xml_file != srcxml_fname:
                copyfile(xml_file, srcxml_fname)  # OSError

            _update_project_file(
                s,
                builddir,
                'source.xml',
                'application/xml',
                'ELBE recipe of the project')

    # TODO what about source.xml ? stored always in db ? version management ?
    #       build/needs_build state ? locking ?

    def create_project(self, builddir):
        # Throws: ElbeDBError, OSError
        directory_created = False

        try:
            with session_scope(self.session) as s:
                if s.query(Project).\
                        filter(Project.builddir == builddir).count() > 0:
                    raise ElbeDBError(
                        f'project {builddir} already exists in database')

                try:
                    os.makedirs(builddir)  # OSError
                    directory_created = True
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        raise ElbeDBError(
                            f'project directory {builddir} already exists')
                    raise

                p = Project(builddir=builddir, status='empty_project')
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
                    f'project {builddir} is not registered in the database')

            if p.status == 'busy':
                raise ElbeDBError(
                    f'cannot delete project {builddir} while it is busy')

            if os.path.exists(builddir):
                # delete project in background to avoid blocking caller for a
                # long time if the project is huge
                t = Thread(target=rmtree, args=[builddir])
                t.start()

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
                    f'project {builddir} is not registered in the database')

            sourcexmlpath = os.path.join(builddir, 'source.xml')
            if os.path.exists(sourcexmlpath):
                p.status = 'needs_build'
            else:
                p.status = 'empty_project'

        if clean:
            targetpath = os.path.join(builddir, 'target')
            if os.path.exists(targetpath):
                rmtree(targetpath)      # OSError

            chrootpath = os.path.join(builddir, 'chroot')
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
            if not os.path.isfile(ep.builddir + '/source.xml') and ep.xml:
                ep.xml.xml.write(ep.builddir + '/source.xml')

            with open(ep.builddir + '/source.xml') as xml_file:
                xml_str = xml_file.read()
                if not project:
                    project = Project(name=ep.xml.text('project/name'),
                                      version=ep.xml.text('project/version'),
                                      builddir=ep.builddir,
                                      xml=xml_str)
                    s.add(project)
                else:
                    project.edit = datetime.utcnow()
                    project.version = ep.xml.text('project/version')
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
                    f'project {builddir} is not registered in the database')

    def set_busy(self, builddir, allowed_status):
        assert 'busy' not in allowed_status
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).with_for_update(). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            if p.status not in allowed_status:
                raise ElbeDBError('project: ' + builddir +
                                  ' set_busy: invalid status: ' + p.status)

            old_status = p.status
            p.status = 'busy'
            return old_status

    def is_busy(self, builddir):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir). \
                    one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            return p.status == 'busy'

    def reset_busy(self, builddir, new_status):
        assert new_status in ('has_changes', 'build_done', 'build_failed')

        with session_scope(self.session) as s:
            try:
                p = s.query(Project).with_for_update(). \
                    filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            if p.status != 'busy':
                raise ElbeDBError(
                    'project: ' +
                    builddir +
                    ' reset_busy: invalid status: ' +
                    p.status)

            p.status = new_status

    def get_project_files(self, builddir):
        # Can throw: ElbeDBError
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            if p.status == 'busy':
                raise ElbeDBError(
                    'project: ' +
                    builddir +
                    ' get_project_files: invalid status: ' +
                    p.status)

            return [ProjectFileData(f) for f in p.files]

    def get_project_file(self, builddir, name):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).filter(Project.builddir == builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {builddir} is not registered in the database')

            if p.status == 'busy':
                raise ElbeDBError(
                    'project: ' +
                    builddir +
                    ' get_project_file: invalid status: ' +
                    p.status)

            try:
                f = s.query(ProjectFile).\
                    filter(ProjectFile.builddir == builddir).\
                    filter(ProjectFile.name == name).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'no file {name} in project {builddir} registered')

            return ProjectFileData(f)

    def update_project_files(self, ep):
        with session_scope(self.session) as s:
            try:
                p = s.query(Project).\
                    filter(Project.builddir == ep.builddir).one()
            except NoResultFound:
                raise ElbeDBError(
                    f'project {ep.builddir} is not registered in the database')

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
                        'application/octet-stream', 'Image')

            # Add other generated files
            _update_project_file(s, p.builddir, 'source.xml',
                                 'application/xml',
                                 'Current source.xml of the project')

            for name in ['chroot', 'target', 'sysroot-target', 'sysroot-host']:

                _update_project_file(s, p.builddir, f'licence-{name}.txt',
                                     'text/plain; charset=utf-8',
                                     'License file')

                _update_project_file(s, p.builddir, f'licence-{name}.xml',
                                     'application/xml',
                                     'xml License file')

            _update_project_file(s, p.builddir, 'validation.txt',
                                 'text/plain; charset=utf-8',
                                 'Package list validation result')

            _update_project_file(s, p.builddir, 'elbe-report.txt',
                                 'text/plain; charset=utf-8',
                                 'Report')

            _update_project_file(s, p.builddir, 'log.txt',
                                 'text/plain; charset=utf-8',
                                 'Log file')

            _update_project_file(s, p.builddir, 'sysroot.tar.xz',
                                 'application/x-xz-compressed-tar',
                                 'sysroot for cross-toolchains')

            sdk = glob.glob(os.path.join(p.builddir, 'setup-elbe-sdk-*.sh'))
            try:
                # throws index error if no  setup-elbe-sdk-* file exists
                # that's ok because it might not yet been built
                sdkname = sdk[0].split('/')[-1]

                _update_project_file(s, p.builddir, sdkname,
                                     'application/x-shellscript',
                                     'SDK Installer')
            except IndexError:
                pass

            _update_project_file(s, p.builddir, 'chroot.tar.xz',
                                 'application/x-xz-compressed-tar',
                                 "chroot for 'native' development")

            # Add Repository iso images
            for img in ep.repo_images:
                name = os.path.basename(img)
                _update_project_file(s, p.builddir, name,
                                     'application/octet-stream',
                                     'Repository IsoImage')

            # Scan pbuilder/build directory if that exists
            if os.path.exists(os.path.join(p.builddir, 'pbuilder', 'result')):
                pbresult_path = os.path.join(p.builddir, 'pbuilder', 'result')
                pfile_path = os.path.join('pbuilder', 'result')
            else:
                pbresult_path = os.path.join(p.builddir, 'pbuilder_cross',
                                             'result')
                pfile_path = os.path.join('pbuilder_cross', 'result')

            if os.path.isdir(pbresult_path):
                for f in os.listdir(pbresult_path):
                    pfile = os.path.join(pfile_path, f)
                    _update_project_file(s, p.builddir, pfile,
                                         'application/octet-stream',
                                         'Pbuilder artifact')

    def add_user(self, name, fullname, password, email):

        pwhash = pbkdf2_sha512.hash(password)

        u = User(name=name,
                 fullname=fullname,
                 pwhash=pwhash,
                 email=email)

        with session_scope(self.session) as s:
            if s.query(User).filter(User.name == name).count() > 0:
                raise ElbeDBError(f'user {name} already exists in the database')
            s.add(u)

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

    @classmethod
    def init_db(cls, name, fullname, password, email):

        if not os.path.exists(cls.db_path):
            try:
                os.makedirs(cls.db_path)
            except OSError as e:
                print(str(e))
                return

        db = ElbeDB()

        try:
            db.add_user(name, fullname, password, email)
        except ElbeDBError as e:
            print(str(e))


class User(Base):  # type: ignore
    __tablename__ = 'users'

    id = Column(Integer, Sequence('article_aid_seq', start=1001, increment=1),
                primary_key=True)

    name = Column(String, unique=True)
    fullname = Column(String)
    pwhash = Column(String)
    email = Column(String)
    projects = relationship('Project', backref='owner')


class Project (Base):  # type: ignore
    __tablename__ = 'projects'

    builddir = Column(String, primary_key=True)
    name = Column(String)
    version = Column(String)
    xml = Column(String)
    status = Column(String)
    edit = Column(DateTime, default=datetime.utcnow)
    files = relationship('ProjectFile', backref='project')


class ProjectData:
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


class ProjectFile (Base):  # type: ignore
    __tablename__ = 'files'

    name = Column(String, primary_key=True)
    builddir = Column(String, ForeignKey('projects.builddir'),
                      primary_key=True)
    mime_type = Column(String, nullable=False)
    description = Column(String)


class ProjectFileData:
    def __init__(self, pf):
        self.name = str(pf.name)
        self.builddir = str(pf.builddir)
        self.mime_type = str(pf.mime_type)
        if pf.description:
            self.description = str(pf.description)
        else:
            self.description = None
