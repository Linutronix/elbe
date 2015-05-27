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

d-i keyboard-configuration/layoutcode string us
d-i keyboard-configuration/xkb-keymap select us

d-i netcfg/get_hostname string elbe-daemon
d-i netcfg/get_domain string localdomain
d-i netcfg/wireless_wep string

d-i debian-installer/locale string en_US
d-i debian-installer/keymap string us
d-i debian-installer/exit/poweroff boolean false
d-i debian-installer/allow_unauthenticated string \
% if prj.has("noauth"):
true
% else:
false
% endif

d-i time/zone string UTC

d-i clock-setup/ntp boolean false
d-i clock-setup/utc boolean true

d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select buildenv
d-i partman-auto/disk string /dev/vda
d-i partman-auto/expert_recipe string buildenv :: 256 1000000 -1 ext3 $primary{ } $bootable{ } method{ format } format{ } use_filesystem{ } filesystem{ ext3 } mountpoint{ / } .
d-i partman/partitioning/confirm_write_new_label boolean true
d-i partman/confirm_write_new_label boolean true
d-i partman/choose_partition select Finish partitioning and write changes to disk
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true
d-i partman-basicfilesystems/no_swap boolean false

d-i base-installer/install-recommends boolean false

d-i grub-installer/skip boolean false
d-i grub-installer/only_debian boolean true
d-i grub-installer/with_other_os boolean true
d-i grub-installer/bootdev  string /dev/vda
d-i lilo-installer/skip boolean true
d-i nobootloader/confirmation_common boolean true

d-i preseed/late_command string /init-elbe.sh

d-i apt-setup/security_host string
d-i apt-setup/services-select multiselect
d-i apt-setup/cdrom/set-first boolean true
d-i apt-setup/cdrom/set-next boolean true

d-i shared/mailname string localhost

d-i quik-installer/oldworld_warning boolean true
d-i quik-installer/non_oldworld_warning boolean true

%if prj.has("mirror/primary_host"):
d-i apt-setup/use_mirror      boolean true
d-i mirror/country            string manual
d-i mirror/http/hostname string ${prj.text("mirror/primary_host").replace("LOCALMACHINE", "10.0.2.2")}
d-i mirror/http/directory string ${prj.text("mirror/primary_path")}
d-i mirror/http/directory string ${prj.text("mirror/primary_path")}
d-i mirror/http/proxy string ${http_proxy}
d-i mirror/protocol string ${prj.text("mirror/primary_proto")}
%endif

<% i=0 %>
% if prj.node("mirror/url-list"):
% for n in prj.node("mirror/url-list"):
<% tmp = n.text("binary").replace("LOCALMACHINE", "10.0.2.2") %>
d-i apt-setup/local${i}/repository string ${tmp.strip()}
d-i apt-setup/local${i}/comment string local server
d-i apt-setup/local${i}/source boolean true
% if n.has("key"):
d-i apt-setup/local${i}/key string ${n.text("key").replace("LOCALMACHINE", "10.0.2.2").strip()}
% endif
<% i+=1 %>
% endfor
% endif
% if prj.node("mirror/cdrom"):
base-config apt-setup/uri_type select cdrom
base-config apt-setup/cd/another boolean false
base-config apt-setup/another boolean false
%  if not prj.has("mirror/primary_host"):
apt-mirror-setup apt-setup/use_mirror boolean false
%  endif
% endif

d-i finish-install/reboot_in_progress note
d-i pkgsel/include string rng-tools btrfs-tools openssh-client \
elbe-soap elbe-buildenv qemu-elbe-user-static \
% for n in pkgs:
% if n.tag == "pkg":
  ${n.et.text} \
% endif
% endfor

passwd passwd/root-password password root
passwd passwd/root-password-again password root
passwd passwd/make-user boolean false

popularity-contest popularity-contest/participate boolean false
tasksel tasksel/first multiselect
console-data console-data/keymap/policy select Don't touch keymap

% for (k, v) in preseed.items():
${k[0]} ${k[1]} ${v[0]} ${v[1]}
% endfor
