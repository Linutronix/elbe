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

import sys
import os
import time
import shutil
import subprocess

class Filesystem(object):
    def __init__(self, path, clean=False):
        self.path = os.path.abspath(path)
        if clean:
            shutil.rmtree(self.path, True)
            os.makedirs(self.path)
            

    def fname(self, path):
        return os.path.join( self.path, path )

    def open(self, path):
        return open( self.fname(path) )

    def isdir(self, path):
        return os.path.isdir( self.fname(path) )

    def islink(self, path):
        return os.path.islink( self.fname(path) )

    def mkdir(self, path):
        os.makedirs( self.fname(path) )

    def stat(self, path):
        return os.stat( self.fname(path) )

    def chown(self, path, uid, gid):
        os.chown( self.fname(path), uid, gid )

    def cat_file(inf):
        content = []
        try:
            f = self.open(inf)
            content = f.readlines();
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

def copy_filelist( src, filelist, dst ):
    for f in file_list:
        f = f.rstrip("\n");
        if src.isdir(f) and not src.islink(f):
            if not dst.isdir(f):
                    dst.makedirs(f)
            st = src.stat(f)
            dst.chown(f, st.st_uid, st.st_gid)
        else:
            subprocess.call(["cp", "-a", "--reflink=auto", src.fname(f), dst.fname(f)])
    # update utime which will change after a file has been copied into
    # the directory
    for f in file_list:
        f = f.rstrip("\n");
        if src.isdir(f) and not src.islink(f):
            shutil.copystat(src.fname(f), dst.fname(f))


def extract_target( src, xml, dst ):
    # create filelists describing the content of the target rfs
    if xml.tgt.has("tighten") or xml.tgt.has("diet"):
        if xml.tgt.has("tighten"):
            f = src.open("opt/elbe/pkg-list")

        elif tgt.has("diet"):

            arch = xml.text("project/buildimage/arch", key="arch")

            # XXX: want to port to python for cache.
            # XXX: would need chroot support as it is.
            os.system("apt-rdepends `cat opt/elbe/pkg-list` | grep -v \"^ \" | uniq >opt/elbe/allpkg-list")
            f = src.open("opt/elbe/allpkg-list")

        file_list = []
        for line in f.readlines():
            line = line.rstrip("\n");
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
        for f in src.listdir(ignore=['target','proc','sys','opt']):
            subprocess.call(["cp", "-a", "--reflink=auto", f, dst.fname('')])

        # and now complete opt but skip opt/elbe
        dst.mkdir("opt")
        for f in os.listdir("opt", ignore=['elbe']):
            subprocess.call(["cp", "-a", "--reflink=auto", f, dst.fname('opt')])

        shutil.copystat(src.fname('opt'), dst.fname('opt'))


    try:
        dst.makedirs("proc")
    except:
        pass
    try:
        dst.makedirs("sys")
    except:
        pass

    if xml.tgt.has("setsel"):
        os.system("mount -o bind /proc %s" %(dst.fname('proc')))
        os.system("mount -o bind /sys %s" %(dst.fname('sys')))

        os.system("chroot %s dpkg --clear-selections" %(dst.fname('')))
        os.system("chroot %s dpkg --set-selections <opt/elbe/pkg-selections" %(dst.fname('')))
        os.system("chroot %s dpkg --purge -a" %(dst.fname('')))

        os.system("umount %s" %(dst.fname('sys')))
        os.system("umount %s" %(dst.fname('proc')))


def dump_elbeversion(xml, dst):
    f = dst.open("etc/elbe_version", "w+")
    f.write("%s %s" %(xml.prj.text("name"), xml.prj.text("version")))
    f.write("this RFS was generated by elbe %s" % (elbe_version))
    f.write(time.strftime("%c"))
    f.close()

def do_elbe_dump(xml, dst):
    dst.remove("opt/elbe/dump.log", noerr=True)

    cmdline = "elbe dump --name \"%s\" --output opt/elbe/elbe-report.txt" %(xml.prj.text("name"))
    cmdline += " --validation opt/elbe/validation.txt --target %s" %(dst.fname(''))
    cmdline += " --finetuning opt/elbe/finetuning.sh"
    cmdline += " --kinitrd \"%s\" opt/elbe/source.xml" %(xml.prj.text("buildimage/kinitrd"))
    if xml.has("archive"):
        cmdline += " --archive opt/elbe/archive.tar.bz2"
    cmdline += " >> opt/elbe/dump.log 2>&1"
    os.system(cmdline)

def create_licenses(src,dst):
    f = dst.open("opt/elbe/licence.txt", "w+")
    for dir in src.listdir("usr/share/doc/", skiplinks=True):
        try:
            lic = open(os.path.join(dir, "copyright"), "r")
            f.write(os.path.basename(dir))
            f.write(":\n================================================================================")
            f.write("\n")
            f.write(lic.read())
            f.write("\n\n")
        except IOError as e:
            os.system("echo Error while processing license file %s: '%s' >> opt/elbe/elbe-report.txt" %
                    (os.path.join(dir, "copyright"), e.strerror))
        finally:
            lic.close()
    f.close()


def part_target(xml,src):

    # create target images and copy the rfs into them
    os.system("opt/elbe/part-target.sh >> opt/elbe/elbe-report.txt 2>&1")

    if xml.has("target/package/tar"):
        os.system("tar cf opt/elbe/target.tar -C %s ." %(src.fname('')))
        os.system("echo /opt/elbe/target.tar >> opt/elbe/files-to-extract")

    if xml.has("target/package/cpio"):
        oldwd = os.getcwd()
        cpio_name = xml.text("target/package/cpio/name")
        os.chdir(src.fname(''))
        os.system("find . -print | cpio -ov -H newc >opt/elbe/%s" % cpio_name)
        os.system("echo /opt/elbe/%s >> opt/elbe/files-to-extract" % cpio_name)
        os.chdir(oldwd)


def extract_some_files(xml, debug, buildchroot):
    os.system("echo '' >> opt/elbe/elbe-report.txt")
    os.system("echo '' >> opt/elbe/elbe-report.txt")
    os.system("echo 'output of dump.py' >> opt/elbe/elbe-report.txt")
    os.system("echo '-----------------' >> opt/elbe/elbe-report.txt")
    os.system("cat /opt/elbe/dump.log   >> opt/elbe/elbe-report.txt")

    os.system("echo '' >> opt/elbe/elbe-report.txt")
    os.system("echo '' >> opt/elbe/elbe-report.txt")
    os.system("echo built with elbe v%s >> opt/elbe/elbe-report.txt" % (elbe_version))

    os.system("echo /opt/elbe/licence.txt >> opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/elbe-report.txt >> opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/source.xml >> opt/elbe/files-to-extract")
    os.system("echo /opt/elbe/validation.txt >> opt/elbe/files-to-extract")

    if debug:
        os.system("echo /var/log/syslog >> opt/elbe/files-to-extract")

    if not buildchroot:
        if xml.text("project/buildimage/arch", key="arch") == "armel":
            os.system("cp -L boot/vmlinuz opt/elbe/vmkernel")
            os.system("cp -L boot/initrd.img opt/elbe/vminitrd")
        elif xml.text("project/buildimage/arch", key="arch") == "powerpc":
            os.system("cp -L boot/vmlinux opt/elbe/vmkernel")
            os.system("cp -L boot/initrd.img /opt/elbe/vminitrd")
        else:
            os.system("cp -L vmlinuz opt/elbe/vmkernel")
            os.system("cp -L initrd.img opt/elbe/vminitrd")
