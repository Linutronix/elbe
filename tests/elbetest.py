
import elbepack
import os
import sys
import shutil

from elbepack.directories import init_directories
from elbepack.shellhelper import system

exe_path = None

def setUpModule():
    global exe_path
    # Properly initialise directories plug
    mod_dir = os.path.dirname (__file__)
    main_dir, _  = os.path.split( mod_dir )
    exe_path  = os.path.join( main_dir, "elbe" )

    init_directories (exe_path)

def validate_example (xml_name):
        system ("%s validate %s" % (exe_path, xml_name))

def test_example_validation ():
    from elbepack.directories import examples_dir
    for e in os.listdir (examples_dir):
        xml_name = os.path.join (examples_dir, e)
        yield validate_example, xml_name

def init_example (xml_name):
    tmpdir = os.getenv( "ELBE_TEST_DIR" )
    assert tmpdir is not None

    dname = os.path.join(tmpdir, "init_test")

    system ('%s init --directory "%s" %s' % (exe_path, dname, xml_name))
    shutil.rmtree (dname)

def test_elbe_init ():
    from elbepack.directories import examples_dir
    for e in os.listdir (examples_dir):
        xml_name = os.path.join (examples_dir, e)
        if e.startswith( "elbe-init" ):
            yield init_example, xml_name

