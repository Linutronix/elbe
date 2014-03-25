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
#

import os
import time
import shutil
import subprocess

from glob import glob

from elbepack.version import elbe_version
from elbepack.hdimg import do_hdimg

class Filesystem(object):
    def __init__(self, path, clean=False):
        self.path = os.path.abspath(path)

        if clean:
            shutil.rmtree(self.path, True)
            os.makedirs(self.path)

    def fname(self, path):
        if path.startswith('/'):
            path = path[1:]
        return os.path.join( self.path, path )

    def open(self, path, mode="r"):
        return open( self.fname(path), mode )

    def isdir(self, path):
        return os.path.isdir( self.fname(path) )

    def islink(self, path):
        return os.path.islink( self.fname(path) )

    def isfile(self, path):
        return os.path.isfile( self.fname(path) )

    def exists(self, path):
        return os.path.exists( self.fname(path) )

    def mkdir(self, path):
        os.makedirs( self.fname(path) )

    def stat(self, path):
        return os.stat( self.fname(path) )

    def chown(self, path, uid, gid):
        os.chown( self.fname(path), uid, gid )

    def chmod(self, path, mode):
        os.chmod( self.fname(path), mode )

    def utime(self, path, times=None):
        os.utime( self.fname(path), times )

    def cat_file(self,inf):
        content = []
        try:
            f = self.open(inf)
            content = f.readlines()
            f.close()
        except IOError:
            pass
        return content

    def remove(self, path, noerr=False):
        try:
            return os.remove( self.fname(path) )
        except:
            if not noerr:
                raise

    def listdir(self, path='', ignore=[], skiplinks=False):
        retval = [os.path.join(self.path, path, x) for x in os.listdir( self.fname(path) ) if not x in ignore]
        if skiplinks:
            retval = filter(lambda x: (not os.path.islink(x)) and os.path.isdir(x), retval)

        return retval

    def glob( self, path ):
        return glob( self.fname( path ) )

    def write_file( self, path, mode, cont ):
        f = self.open( path, "w" )
        f.write(cont)
        f.close()
        self.chmod( path, mode )

    def read_file( self, path ):
        fp = self.open( path, "r" )
        retval = fp.read()
        fp.close()
        return retval

    def mkdir_p (self, newdir, mode=0777):
        """works the way a good mkdir -p would...
                - already exists, silently complete
                - regular file in the way, raise an exception
                - parent directory(ies) does not exist, make them as well
        """
        if self.isdir (newdir):
            pass
        elif self.isfile (newdir):
            raise OSError ("a file with the same name as the desired " \
                    "dir, '%s', already exists. in RFS %s" % (newdir, self.path))
        else:
            self.mkdir (newdir)
            self.chmod (newdir,mode)

    def touch_file (self,fname):
        if self.exists (fname):
            self.utime(fname)
        else:
            fp = self.open(fname,"w")
            fp.close ()

    def walk_files(self, directory='', exclude_dirs=[]):
        dirname = self.fname(directory)
        if dirname=="/":
            striplen = 0
        else:
            striplen = len(dirname)
        for dirpath, dirnames, filenames in os.walk(dirname):
            subpath = dirpath[striplen:]
            if len(subpath) == 0:
                subpath="/"

            deldirs = []
            for d in dirnames:
                dpath = os.path.join( subpath, d )
                if dpath in exclude_dirs:
                    deldirs.append(d)

            for d in deldirs:
                dirnames.remove(d)

            for f in filenames:
                fpath = os.path.join( subpath, f )
                realpath = os.path.join( dirpath, f )
                yield "/" + fpath, realpath

    def mtime_snap(self, dirname='', exclude_dirs=[]):
        mtime_index = {}

        for fpath, realpath in self.walk_files(dirname,exclude_dirs):
            stat = os.lstat(realpath)
            mtime_index[fpath] = stat.st_mtime

        return mtime_index

    # XXX: dump_elbeversion is elbe specific, should not be in Filesystem
    def dump_elbeversion(self, xml):
        f = self.open("etc/elbe_version", "w+")
        f.write("%s %s\n" %(xml.prj.text("name"), xml.prj.text("version")))
        f.write("this RFS was generated by elbe %s\n" % (elbe_version))
        f.write(time.strftime("%c\n"))
        f.close()

        elbe_base = self.open("etc/elbe_base.xml", "wb")
        xml.xml.write(elbe_base)

def copy_filelist( src, filelist, dst ):
    for f in filelist:
        f = f.rstrip("\n")
        if src.isdir(f) and not src.islink(f):
            if not dst.isdir(f):
                dst.makedirs(f)
            st = src.stat(f)
            dst.chown(f, st.st_uid, st.st_gid)
        else:
            subprocess.call(["cp", "-a", "--reflink=auto", src.fname(f), dst.fname(f)])
    # update utime which will change after a file has been copied into
    # the directory
    for f in filelist:
        f = f.rstrip("\n")
        if src.isdir(f) and not src.islink(f):
            shutil.copystat(src.fname(f), dst.fname(f))


def extract_target( src, xml, dst, log ):
    # create filelists describing the content of the target rfs
    if xml.tgt.has("tighten") or xml.tgt.has("diet"):
        if xml.tgt.has("tighten"):
            f = src.open("opt/elbe/pkg-list")

        elif xml.tgt.has("diet"):

            arch = xml.text("project/buildimage/arch", key="arch")

            # XXX: want to port to python for cache.
            # XXX: would need chroot support as it is.
            log.do("apt-rdepends `cat opt/elbe/pkg-list` | grep -v \"^ \" | uniq >opt/elbe/allpkg-list")
            f = src.open("opt/elbe/allpkg-list")

        file_list = []
        for line in f.readlines():
            line = line.rstrip("\n")
            file_list += src.cat_file("var/lib/dpkg/info/%s.list" %(line))
            file_list += src.cat_file("var/lib/dpkg/info/%s.conffiles" %(line))

            file_list += src.cat_file("var/lib/dpkg/info/%s:%s.list" %(line, arch))
            file_list += src.cat_file("var/lib/dpkg/info/%s:%s.conffiles" %(line, arch))

        f.close()

        if xml.tgt.has("diet"):
            src.remove("opt/elbe/allpkg-list")

        file_list = list(sorted(set(file_list)))
        copy_filelist(src, file_list, dst)
    else:
        # first copy most diretories
        for f in src.listdir():
            subprocess.call(["cp", "-a", "--reflink=auto", f, dst.fname('')])

    try:
        dst.makedirs("proc")
    except:
        pass
    try:
        dst.makedirs("sys")
    except:
        pass

    if xml.tgt.has("setsel"):
        log.do("mount -o bind /proc %s" %(dst.fname('proc')))
        log.do("mount -o bind /sys %s" %(dst.fname('sys')))

        log.do("chroot %s dpkg --clear-selections" %(dst.fname('')))
        log.do("chroot %s dpkg --set-selections <opt/elbe/pkg-selections" %(dst.fname('')))
        log.do("chroot %s dpkg --purge -a" %(dst.fname('')))

        log.do("umount %s" %(dst.fname('sys')))
        log.do("umount %s" %(dst.fname('proc')))

class ChRootFilesystem(Filesystem):
    def __init__(self, path, interpreter=None, clean=False):
        Filesystem.__init__(self,path,clean)
        self.interpreter = interpreter
        self.cwd = os.open ("/", os.O_RDONLY)
        self.inchroot = False

    def __delete__ (self):
        os.close (self.cwd)

    def __enter__(self):
        if self.interpreter:
            os.system ('cp /usr/bin/%s %s' % (self.interpreter,
                self.fname( "usr/bin" )) )
        self.mount()
        return self

    def __exit__(self, type, value, traceback):
        if self.inchroot:
            self.leave_chroot()
        self.umount()
        if self.interpreter:
            os.system( 'rm -f %s' %
                        os.path.join(self.path, "usr/bin/"+self.interpreter) )
    def mount(self):
        if self.path == '/':
            return
        try:
            os.system ("mount -t proc none %s/proc" % self.path)
            os.system ("mount -t sysfs none %s/sys" % self.path)
            os.system ("mount -o bind /dev %s/dev" % self.path)
            os.system ("mount -o bind /dev/pts %s/dev/pts" % self.path)
        except:
            self.umount ()
            raise

    def enter_chroot (self):
        assert not self.inchroot

        os.environ["LANG"] = "C"
        os.environ["LANGUAGE"] = "C"
        os.environ["LC_ALL"] = "C"

        os.chdir(self.path)
        self.inchroot = True

        if self.path == '/':
            return

        os.chroot(self.path)


    def _umount (self, path):
        if os.path.ismount (path):
            os.system("umount %s" % path)

    def umount (self):
        if self.path == '/':
            return
        self._umount ("%s/proc/sys/fs/binfmt_misc" % self.path)
        self._umount ("%s/proc" % self.path)
        self._umount ("%s/sys" % self.path)
        self._umount ("%s/dev/pts" % self.path)
        self._umount ("%s/dev" % self.path)

    def leave_chroot (self):
        assert self.inchroot

        os.fchdir (self.cwd)

        self.inchroot = False
        if self.path == '/':
            return

        os.chroot (".")

class TargetFs(ChRootFilesystem):
    def __init__(self, path, log, xml, clean=True):
        ChRootFilesystem.__init__(self, path, xml.defs["userinterpr"], clean)
        self.log = log
        self.xml = xml

    def part_target(self, targetdir, skip_grub):

        # create target images and copy the rfs into them
        do_hdimg( self.log, self.xml, targetdir, self, skip_grub )

        if self.xml.has("target/package/tar"):
            self.log.do("tar cfz %s/target.tar.gz -C %s ." %(targetdir,self.fname('')))

        if self.xml.has("target/package/cpio"):
            oldwd = os.getcwd()
            cpio_name = self.xml.text("target/package/cpio/name")
            os.chdir(self.fname(''))
            self.log.do("find . -print | cpio -ov -H newc >%s" % os.path.join(targetdir,cpio_name) )
            os.chdir(oldwd)

class BuildImgFs(ChRootFilesystem):
    def __init__(self, path, interpreter):
        ChRootFilesystem.__init__(self, path, interpreter)

    def write_licenses(self, f, log):
        for dir in self.listdir("usr/share/doc/", skiplinks=True):
            try:
                lic = open(os.path.join(dir, "copyright"), "r")
                f.write(os.path.basename(dir))
                f.write(":\n================================================================================")
                f.write("\n")
                f.write(lic.read())
                f.write("\n\n")
            except IOError as e:
                log.printo( "Error while processing license file %s: '%s'" %
                        (os.path.join(dir, "copyright"), e.strerror))
            finally:
                lic.close()
