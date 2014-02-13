import logging
logger = logging.getLogger(__name__)
import os
import sys
import uuid
from elbepack.expect import spawn
import pexpect
import apt
import ConfigParser
import shutil
import uuid

# sys.path.append('./')

from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.serving import run_simple

from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.error import ResourceNotFoundError
from spyne.error import ValidationError
from spyne.model.binary import ByteArray
from spyne.model.primitive import Unicode
from spyne.model.primitive import Mandatory
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap import Soap11
from spyne.model.binary import File

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.events import PatternMatchingEventHandler


from elbepack.treeutils import etree
from elbepack import virtapt

from optparse import OptionParser
from datetime import datetime
from elbepack.validate import validate_xml
from elbepack.xmldefaults import ElbeDefaults
import apt_pkg

BLOCK_SIZE = 8192

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        tmp_path = os.path.join('/tmp', '%s' % uuid.uuid4())
        if not os.path.isdir(tmp_path):
            os.mkdir(tmp_path)

        print 'event: %s tmp path: %s ' %(event.src_path,tmp_path)
        self.shellcmds = []
        self.log = open(tmp_path + '/logfile.txt','w')

        ext_cmd = 'tar -xf ' + '/' + event.src_path + ' -C ' + tmp_path
        print 'extract cmd: %s ' %(ext_cmd)

        os.system('tar -xf ' + '/' + event.src_path + ' -C ' + tmp_path)

        print 'reprepro -b %s *.deb' %(tmp_path)

#        os.system('reprepro -b %s *.deb' %(tmp_path))

        inst_fname = tmp_path + '/install.txt'
        print 'install file name: %s ' %(inst_fname)
        packets = []

        with open(inst_fname, 'r') as inputfile:
            for line in inputfile:
                packets.append(line.strip('\n').split(' '))

        # build install string

        nr = 0
        inst_str = 'apt-get install '
        for p in packets:
            if nr is not 0:
                print 'Update: %s from: %s to %s ' %(p[0],p[2],p[1])
                inst_str += p[0] + '=' + p[1] + ' '
            nr += 1

        print "install str: %s "%(inst_str)
        print "source.xml name: %s" %(packets[0][0])
        os.system(inst_str)
        # return value check if good overwrite current source.xml
        os.system('cp ' + tmp_path + '/source.xml /var/elbe/versions/source_'+packets[0][0])

        self.envargs = ''
        # unzip upd file to tmp/uuid

        # parse install file


    def on_deleted(self, event):
        print event

    def on_moved(self, event):
        print event


class FileServices(ServiceBase):

    @rpc(Mandatory.Unicode, _returns=ByteArray(encoding='hex'))
    def get(ctx, file_name):  # get files from target
        path = os.path.join(os.path.abspath('./files'), file_name)
        if not path.startswith(os.path.abspath('./files')):
            raise ValidationError(file_name)

        try:
            f = open(path, 'r')
        except IOError:
            raise ResourceNotFoundError(file_name)

        ctx.transport.resp_headers['Content-Disposition'] = (
                                         'attachment; filename=%s;' % file_name)

        data = f.read(BLOCK_SIZE)
        while len(data) > 0:
            yield data

            data = f.read(BLOCK_SIZE)

        f.close()

    @rpc(Unicode, Unicode, Unicode, ByteArray(encoding='hex'))
    def add(ctx, person_type, action, file_name, file_data):  # upload files to target
        logger.info("Person Type: %r" % person_type)
        logger.info("Action: %r" % action)

        path = os.path.join(os.path.abspath('./files'), file_name)
        if not path.startswith(os.path.abspath('./files')):
            raise ValidationError(file_name)

        f = open(path, 'w') # if this fails, the client will see an
                            # internal error.

        try:
            for data in file_data:
                logger.debug("Data: %r" % data)
                f.write(data)


            logger.debug("File written: %r" % file_name)
            logger.debug("File data: %s" % file_data)
            f.close()

        except:
            f.close()
            os.remove(file_name)
            logger.debug("File removed: %r" % file_name)
            raise # again, the client will see an internal error.

    @rpc(Unicode, Unicode, Unicode, ByteArray(encoding='hex'))
    def down_grade(ctx,file_data):

        path = os.path.join('/tmp', '%s' % uuid.uuid4())
        f = open(path, 'w') # if this fails, the client will see an
                            # internal error.

        try:
            for data in file_data:
                logger.debug("Data: %r" % data)
                f.write(data)


            logger.debug("File written: %r" % file_name)
            logger.debug("File data: %s" % file_data)
            f.close()

        except:
            f.close()
            os.remove(file_name)
            logger.debug("File removed: %r" % file_name)
            raise # again, the client will see an internal error.

        xml = etree(path + '/source.xml')

        if xml.has( "project/buildtype" ):
            buildtype = xml.text( "/project/buildtype" )
        else:
            buildtype = "nodefaults"

        defs = ElbeDefaults( buildtype )

        arch  = xml.text("project/buildimage/arch", default=defs, key="arch")
        suite = xml.text("project/suite")

        name  = xml.text("project/name", default=defs, key="name")

        apt_sources = xml.text("sources_list")
        apt_prefs   = xml.text("apt_prefs")

        fullp = xml.node("fullpkgs")


    @rpc(Unicode, Unicode, Unicode, ByteArray(encoding='hex'))
    def create_master(ctx):

#        path = '/tmp/' + uuid.uuid4()

#        f = open(path, 'w') # if this fails, the client will see an
                            # internal error.
#        dst_path = '/opt/elbe/source.xml_' + uuid.uuid4()

#        try:
#            for data in file_data:
#                logger.debug("Data: %r" % data)
#                f.write(data)


#            logger.debug("File written: %r" % file_name)
#            logger.debug("File data: %s" % file_data)
#            f.close()

#        except:
#            f.close()
#            os.remove(file_name)
#            logger.debug("File removed: %r" % file_name)
#            raise # again, the client will see an internal error.

#        shutil.copy('/opt/elbe/source.xml', dst_path)
#        shutil.copy(path,'/opt/elbe/source.xml')

        os.system('elbe create-target-rfs -t /target -b /opt/elbe/source.xml ')



def run_command( argv ):
    cfg_path = '/etc/default/'     # source.xml, fingerprint,
                                # elbe-updated/config
                                # ... fingerprint
                                # ... repo directory
                                # ... fingerprint
                                # ... url for status report

    # get update path
    # config = ConfigParser.RawConfigParser()
    # config.read('/etc/default/elbe-updated.conf')

    # update_dir = config.get('elbe_updated', 'file_path')
    # port = config.get('elbe_soap', 'port')
    update_dir = "/tmp/elbe"
    port = 1234

    if not os.path.isdir(update_dir):
        # copy source xml
        # check if xml is up to date ?
        # check repo is installed
        # check sign key
        os.mkdir(update_dir)

    observer = Observer()
    observer.schedule(Handler(), path=update_dir, recursive=True)
    observer.start()

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    filemgr_app = WsgiApplication(Application([FileServices],
            tns='spyne.examples.file_manager',
            in_protocol=Soap11(),
#            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        ))

    try:
        os.makedirs('./files')
    except OSError:
        pass

    wsgi_app = DispatcherMiddleware(NotFound(), {'/filemgr': filemgr_app})
    return run_simple('localhost', port, wsgi_app, static_files={'/': 'static'},
                                                                  threaded=True)
