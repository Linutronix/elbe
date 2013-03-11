## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (C) 2013  Linutronix GmbH
##
## This file is part of ELBE.
##
## ELBE is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## ELBE is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with ELBE.  If not, see <http://www.gnu.org/licenses/>.
##
#! /bin/sh

rm -rf /target
mkdir -p /target
rm -f /opt/elbe/filelist

# purge packages if nessesary
/opt/elbe/purge.sh



# create filelists describing the content of the target rfs
% if tgt.has("tighten"):
sed 's@^\(.*\)@cat /var/lib/dpkg/info/\1.list@' /opt/elbe/pkg-list | sh >> /opt/elbe/filelist
sed 's@^\(.*\)@cat /var/lib/dpkg/info/\1.conffiles@' /opt/elbe/pkg-list | sh >> /opt/elbe/filelist

% elif tgt.has("diet"):
apt-rdepends `cat /opt/elbe/pkg-list` | grep -v "^ " | uniq >/opt/elbe/allpkg-list
sed 's@^\(.*\)@cat /var/lib/dpkg/info/\1.list@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist
sed 's@^\(.*\)@cat /var/lib/dpkg/info/\1.conffiles@' /opt/elbe/allpkg-list | sh >> /opt/elbe/filelist

% else:
cd /
ls -A1 / | grep -v target | grep -v proc | grep -v sys | xargs find >> /opt/elbe/filelist
cd -
% endif

# build and install packages from version control systems
cd /tmp
mkdir -v -p /opt/elbe/builds >> build.txt 2>&1
% for git in tgt.node("pkg-list"):
% if git.tag == "git-src":
git clone ${git.text("url")} git-src >> build.txt 2>&1
if [ "$?" -ne "0" ]; then
	echo 'git repo ${git.text("url")} unreachable' >> build.txt 2>&1
else
	cd git-src
% if git.has("tag"):
	git checkout -b build-tag ${git.text("tag")} >> build.txt 2>&1
% endif
	dpkg-buildpackage >> build.txt 2>&1
	cd ..
	rm -rf git-src
	dpkg -i --force-all *.deb  >> build.txt 2>&1
	apt-get install -f >> build.txt 2>&1
	DEBS=`ls -1 *.deb | grep -v "\-dev"`
	for DEB in $DEBS; do
		dpkg --contents $DEB | awk '{ print $6 }' | \
			sed s/^\.// >> /opt/elbe/filelist
	done;
	mv -v *.deb *.dsc *.changes *.tar.gz /opt/elbe/builds >> build.txt 2>&1
fi
% endif
% endfor

% for svn in tgt.node("pkg-list"):
% if svn.tag == "svn-src":
svn checkout ${svn.text("url")} \
% if svn.has("rev"):
 -r${svn.text("rev")} \
% endif
svn-src >> build.txt 2>&1
if [ "$?" -ne "0" ]; then
	echo 'svn repository ${svn.text("url")} unreachable' >> build.txt 2>&1
else
	cd svn-src
	dpkg-buildpackage >> build.txt 2>&1
	cd ..
	rm -rf svn-src
	dpkg -i --force-all *.deb >> build.txt 2>&1
	apt-get install -f >> build.txt 2>&1
	DEBS=`ls -1 *.deb | grep -v "\-dev"`
	for DEB in $DEBS; do
		dpkg --contents $DEB | awk '{ print $6 }' | \
			sed s/^\.// >> /opt/elbe/filelist
	done;
	mv -v *.deb *.dsc *.changes *.tar.gz /opt/elbe/builds >> build.txt 2>&1
fi
% endif
% endfor


# purge packages if nessesary
/opt/elbe/purge.sh


# create target rfs
cd /
rsync -a --files-from=/opt/elbe/filelist / /target


mkdir /target/proc
mkdir /target/sys

% if tgt.has("setsel"):
mount -o bind /proc /target/proc
mount -o bind /sys /target/sys

chroot /target dpkg --clear-selections
chroot /target dpkg --set-selections </opt/elbe/pkg-selections
chroot /target dpkg --purge -a

umount /target/proc
umount /target/sys
% endif

% if xml.has("archive"):
python /opt/elbe/dump.py --name "${prj.text("name")}" --output /opt/elbe/elbe-report.txt --validation /opt/elbe/validation.txt --target /target --finetuning /opt/elbe/finetuning.sh --archive /opt/elbe/archive.tar.bz2 --kinitrd ${prj.text("buildimage/kinitrd")} /opt/elbe/source.xml 
% else:
python /opt/elbe/dump.py --name "${prj.text("name")}" --output /opt/elbe/elbe-report.txt --validation /opt/elbe/validation.txt --target /target --finetuning /opt/elbe/finetuning.sh --kinitrd ${prj.text("buildimage/kinitrd")} /opt/elbe/source.xml 
% endif

rm -rf /opt/elbe/licence.txt

find /usr/share/doc -name copyright -exec \
	/opt/elbe/print_licence.sh {} \; >> /opt/elbe/licence.txt

# create target images and copy the rfs into them
/opt/elbe/part-target.sh >> /opt/elbe/elbe-report.txt 2>&1

% if xml.has("target/package/tar"):
tar cf /opt/elbe/target.tar -C /target .
echo /opt/elbe/target.tar >> /opt/elbe/files-to-extract
% endif

% if xml.has("target/package/cpio"):
cd /target
find . -print | cpio -ov -H newc >/opt/elbe/${xml.text("target/package/cpio/name")}
echo /opt/elbe/${xml.text("target/package/cpio/name")} >> /opt/elbe/files-to-extract
% endif

% if xml.has("target/pkg-list/git-src") or xml.has("target/pkg-list/svn-src"):
tar cf /opt/elbe/builds.tar -C /opt/elbe/builds .
echo /opt/elbe/builds.tar >> /opt/elbe/files-to-extract
% endif

if [ -f build.txt ]; then
echo "" >> /opt/elbe/elbe-report.txt
echo "package builds from version control systems" >> /opt/elbe/elbe-report.txt
echo "-------------------------------------------" >> /opt/elbe/elbe-report.txt
echo "" >> /opt/elbe/elbe-report.txt
echo "================================================================" >> /opt/elbe/elbe-report.txt
cat build.txt >> /opt/elbe/elbe-report.txt
echo "================================================================" >> /opt/elbe/elbe-report.txt
echo "" >> /opt/elbe/elbe-report.txt

fi

echo /opt/elbe/licence.txt >> /opt/elbe/files-to-extract
echo /opt/elbe/elbe-report.txt >> /opt/elbe/files-to-extract
echo /opt/elbe/source.xml >> /opt/elbe/files-to-extract
echo /opt/elbe/validation.txt >> /opt/elbe/files-to-extract


% if opt.debug:
echo /var/log/syslog >> /opt/elbe/files-to-extract
% endif


% if xml.text("project/buildimage/arch") == "armel":
	echo /boot/initrd.img-2.6.32-5-versatile >> /opt/elbe/files-to-extract
	echo /boot/vmlinuz-2.6.32-5-versatile >> /opt/elbe/files-to-extract
% elif xml.text("project/buildimage/arch") == "powerpc":
	echo /boot/initrd.img-2.6.32-5-powerpc >> /opt/elbe/files-to-extract
	echo /boot/vmlinux-2.6.32-5-powerpc >> /opt/elbe/files-to-extract
% endif
