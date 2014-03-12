from elbepack import rfs
from elbepack import elbexml
from elbepack import filesystem
from elbepack import asciidoclog

import os
import time

xml = elbexml.ElbeXML('source.xml')
log = asciidoclog.ASCIIDocLog( "update.log" )
br = rfs.BuildEnv(xml, log, 'chroot')

from elbepack.rpcaptcache import get_rpcaptcache

# Use "with br" to mount the necessary bind mounts
with br:
    cc = get_rpcaptcache(br.rfs, "aptcache.log", "armel")
    print "SECTIONS: ", cc.get_sections()
    time.sleep (2)
    print "SHELLS: ", cc.get_pkglist('shells')
    time.sleep (2)
    print "QUICKPLOT: ", cc.get_dependencies('quickplot')
    time.sleep (2)
    cc.mark_install('quickplot','2')
    cc.commit()
    #cc.mark_delete('quickplot','2')
    #cc.commit()

