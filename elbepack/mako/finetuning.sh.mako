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
#!/bin/bash

cd /target
unset -v $(set | sed -e 's/=.*//g' | egrep -v '^(BASH*|HO*|IFS|PATH*|PWD|EUID|PPID|UID|SHELL*|TERM*)')
. /etc/profile


% if fine:
% for n in fine:
  % if n.tag == "rm":
    rm -rvf /target/${n.et.text}
  % endif
  % if n.tag == "cp":
    echo "cp "
    cp -av /target/${n.et.attrib["path"]} /target/${n.et.text}
  % endif
  % if n.tag == "mv":
    echo "mv "
    mv -v /target/${n.et.attrib["path"]} /target/${n.et.text}
  % endif
  % if n.tag == "mkdir":
    mkdir -pv /target/${n.et.text}
  % endif
  % if n.tag == "command":
    ${n.et.text}
  % endif
  % if n.tag == "purge":
    mount -o bind /proc /target/proc
    mount -o bind /sys /target/sys

    chroot /target dpkg --purge ${n.et.text}

    umount /target/proc
    umount /target/sys
  % endif
% endfor
% endif

echo "copy elbe generated fstab"
cp -v /opt/elbe/fstab /target/etc
