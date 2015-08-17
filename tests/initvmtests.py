
import elbepack
import os
import sys
import shutil

from elbepack.directories import init_directories
from elbepack.shellhelper import system

exe_path = None

def setup():
    global exe_path
    # Properly initialise directories plug
    mod_dir = os.path.dirname (__file__)
    main_dir, _  = os.path.split( mod_dir )
    exe_path  = os.path.join( main_dir, "elbe" )

    init_directories (exe_path)

    tmpdir = os.getenv( "ELBE_TEST_DIR" )
    assert tmpdir is not None

    dname = os.path.join(tmpdir, "initvm_test")

    from elbepack.directories import examples_dir
    xml_name = os.path.join (examples_dir, "elbe-init-with-ssh.xml")
    system ('%s initvm create --directory "%s" %s' % (exe_path, dname, xml_name))

def teardown():
    tmpdir = os.getenv( "ELBE_TEST_DIR" )
    assert tmpdir is not None

    dname = os.path.join(tmpdir, "initvm_test")
    shutil.rmtree (dname)


def test_submit ():
    from elbepack.directories import examples_dir
    xml_name = os.path.join (examples_dir, "rescue.xml")

    system ("%s initvm submit %s" % (exe_path, xml_name))

