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
#!/bin/sh

# Download the kinitrd into /var/cache/apt
DEBCONF_REDIR= apt-get -d -y --force-yes install ${prj.text("buildimage/kinitrd")}

mkdir -p /opt/elbe/cdrom/conf


# Sort debootstrap packages from normal packages

mkdir -p /opt/elbe/debootstrap

% if prj.has("mirror/primary_host"):
# This Fails if its split into multiple lines
# Please leave it a single line.
% if prj.text("suite") == "wheezy":
for p in `ls /var/cache/apt/archives/*.deb`; do if grep `basename $p | sed "s/.%3a//"` /var/lib/apt/lists/${prj.text("mirror/primary_host")}_${prj.text("mirror/primary_path").replace('/','_').rstrip('_')}_dists_${prj.text("suite")}_main_binary-${prj.text("buildimage/arch", default=defs, key="arch")}_Packages > /dev/null ; then mv $p /opt/elbe/debootstrap; fi; done
% else:
for p in `ls /var/cache/apt/archives/*.deb`; do if grep `basename $p | sed "s/.%3a//"` /var/lib/apt/lists/${prj.text("mirror/primary_host")}_${prj.text("mirror/primary_path").replace('/','_').strip('_')}_dists_${prj.text("suite")}_main_binary-${prj.text("buildimage/arch", default=defs, key="arch")}_Packages > /dev/null ; then mv $p /opt/elbe/debootstrap; fi; done
% endif

# Move kinitrd to debootstrap also.
mv /var/cache/apt/archives/${prj.text("buildimage/kinitrd")}*.deb /opt/elbe/debootstrap
% endif

cat > /opt/elbe/cdrom/conf/distributions <<EOF
Origin: Debian
Label: Debian-All
Suite: stable
Codename: ${prj.text("suite")}
Version: 6.0
Architectures: ${prj.text("buildimage/arch", default=defs, key="arch")}
Components: main added
UDebComponents: main
Description: Debian SQ
% if prj.has("mirror/cdrom"):
Update: cdrom mover
% else:
Update: ftp mover added
% endif
Contents: udebs

EOF

cat > /opt/elbe/cdrom/conf/updates <<EOF
Name: cdrom
Method: file:///mnt/debian
VerifyRelease: blindtrust
#GetInRelease: no
Components: main>main added>added
UDebComponents: main>main

Name: mover
Method: file:///opt/elbe/debootstrap
Suite: ./
VerifyRelease: blindtrust
#GetInRelease: no
Flat: main

Name: added
Method: file:///var/cache/apt/archives
Suite: ./
VerifyRelease: blindtrust
#GetInRelease: no
Flat: added


% if prj.has("mirror/primary_host"):
Name: ftp
Method: ${prj.text("mirror/primary_proto")}://${prj.text("mirror/primary_host")}/${prj.text("mirror/primary_path")}
VerifyRelease: blindtrust
#GetInRelease: no
Components:
UDebComponents: main>main
% endif

EOF

cd /var/cache/apt/archives
rm -f Packages
rm -f Packages.gz
apt-ftparchive packages . > Packages
gzip -9 Packages
apt-ftparchive release . > Release

cd /opt/elbe/debootstrap
rm -f Packages
rm -f Packages.gz
apt-ftparchive packages . > Packages
gzip -9 Packages
apt-ftparchive release . > Release
cd /opt/elbe


reprepro -b /opt/elbe/cdrom update

rm -f /var/cache/apt/archives/Packages.gz
rm -f /var/cache/apt/archives/Release


mkdir -p /opt/elbe/cdrom/.disk
echo main > /opt/elbe/cdrom/.disk/base_installable
echo main > /opt/elbe/cdrom/.disk/base_components
echo not_complete > /opt/elbe/cdrom/.disk/cd_type
echo "elbe inst cdrom" > /opt/elbe/cdrom/.disk/info

cp /opt/elbe/source.xml /opt/elbe/cdrom
md5sum /opt/elbe/cdrom/source.xml > /opt/elbe/cdrom/source.md5


ln -s . /opt/elbe/cdrom/debian

genisoimage -o /opt/elbe/install.iso -R -J -joliet-long /opt/elbe/cdrom
echo /opt/elbe/install.iso >> /opt/elbe/files-to-extract

% if opt.buildsources:
mkdir -p /opt/elbe/source
 
dpkg --get-selections | awk '{print $1}' > /opt/elbe/pkg-list.actual
cd /opt/elbe/source
awk '{print "apt-get -d source "$1}' /opt/elbe/pkg-list.actual | sh
cd /opt/elbe
dpkg-scansources source /dev/null | gzip -9c > source/Sources.gz
genisoimage -o /opt/elbe/source.iso -J -R source
echo /opt/elbe/source.iso >> /opt/elbe/files-to-extract
% endif

