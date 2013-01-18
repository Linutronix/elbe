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
apt-get -d -y install ${prj.text("buildimage/kinitrd")}

mkdir -p /opt/elbe/cdrom/conf

cat > /opt/elbe/cdrom/conf/distributions <<EOF
Origin: Debian
Label: Debian-All
Suite: stable
Codename: ${prj.text("suite")}
Version: 6.0
Architectures: ${prj.text("buildimage/arch")}
Components: main
UDebComponents: main
Description: Debian SQ
% if prj.has("mirror/cdrom"):
Update: cdrom mover
% else:
Update: ftp mover
% endif
Contents: udebs

EOF

cat > /opt/elbe/cdrom/conf/updates <<EOF
Name: cdrom
Method: file:///mnt/debian
VerifyRelease: blindtrust
#GetInRelease: no
Components: main>main
UDebComponents: main>main

Name: mover
Method: file:///mirrors/debian
VerifyRelease: blindtrust
#GetInRelease: no
Components: main>main
UDebComponents:


Name: ftp
Method: http://ftp.de.debian.org/debian
VerifyRelease: blindtrust
#GetInRelease: no
Components:
UDebComponents: main>main

EOF

sed -i "s/APTSITES=.*$/APTSITES=*/" /etc/apt-move.conf
apt-move update
ln -s stable /mirrors/debian/dists/${prj.text("suite")}

reprepro -b /opt/elbe/cdrom update

mkdir -p /opt/elbe/cdrom/.disk
echo main > /opt/elbe/cdrom/.disk/base_installable
echo main > /opt/elbe/cdrom/.disk/base_components
echo not_complete > /opt/elbe/cdrom/.disk/cd_type
echo "elbe inst cdrom" > /opt/elbe/cdrom/.disk/info

cp /opt/elbe/source.xml /opt/elbe/cdrom
md5sum /opt/elbe/cdrom/source.xml > /opt/elbe/cdrom/source.md5


ln -s . /opt/elbe/cdrom/debian

genisoimage -o /opt/elbe/install.iso -R -J -joliet-long /opt/elbe/cdrom

% if opt.buildsources:
mkdir -p /opt/elbe/source
 
dpkg --get-selections | awk '{print $1}' > /opt/elbe/pkg-list.actual
cd /opt/elbe/source
awk '{print "apt-get -d source "$1}' /opt/elbe/pkg-list.actual | sh
cd /opt/elbe
dpkg-scansources source /dev/null | gzip -9c > source/Sources.gz
genisoimage -o /opt/elbe/source.iso -J -R source
% endif

