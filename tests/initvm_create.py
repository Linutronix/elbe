

import elbepack
import os
import sys
import shutil
from time import sleep

from elbepack.directories import init_directories
from elbepack.shellhelper import system

exe_path = None

def test_initvm():
    try:
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
        system ('%s initvm create --devel --directory "%s" %s' % (exe_path, dname, xml_name))
    except:
        system ("%s control shutdown_initvm" % (exe_path), allow_fail=True)
        sleep (10)
        tmpdir = os.getenv( "ELBE_TEST_DIR" )
        assert tmpdir is not None

        dname = os.path.join(tmpdir, "initvm_test")
        shutil.rmtree (dname)
        raise


