## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2014-2015 Torben Hohn <torbenh@linutronix.de>
## Copyright (c) 2014, 2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2017 John Ogness <john.ogness@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
<%
  from elbepack.version import elbe_version, elbe_initvm_packagelist
  from elbepack.filesystem import size_to_int
  swap = size_to_int(prj.text('swap-size', default=defs, key='swap-size')) // 1024 // 1024
%>
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
d-i partman-auto/expert_recipe string buildenv :: \
%if swap != 0:
  ${swap} ${swap} ${swap} linux-swap $primary{ } method{ swap } format{ } . \
%endif
256 1000000 -1 ext3 $primary{ } $bootable{ } method{ format } format{ } use_filesystem{ } filesystem{ ext3 } mountpoint{ / } .
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
% if n.has("binary"):
<% tmp = n.text("binary").replace("LOCALMACHINE", "10.0.2.2") %>
d-i apt-setup/local${i}/repository string ${tmp.strip()}
d-i apt-setup/local${i}/comment string local server
d-i apt-setup/local${i}/source boolean true
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

<%
    def pkg2preseed (n):
        # we have a set of old elbe files, which have pkgnames like:
        #      pkgname/jessie-backports
        # be backwards compatible and support them
        pkgsplit = n.et.text.split ('/')

        pkgname = pkgsplit[0]

        if len (pkgsplit) > 1:
            pkgrel = pkgsplit[1]
        else:
            pkgrel = None

        # pkg pin attrib overrides /
        if 'pin' in n.et.attrib:
            pkgrel =  n.et.attrib['pin']

        # pkg attrib version wins over all and it can also be
        # used with cdrom build
        if 'version' in n.et.attrib:
            return pkgname + '=' + n.et.attrib['version']

        # for a cdrom build, the pkgrel is reset to None because the
        # cdrom does not have the release information anymore
        if not prj.has("mirror/primary_host") and prj.node("mirror/cdrom"):
            pkgrel = None

        if pkgrel is None:
            return pkgname

        return pkgname + '/' + pkgrel
%>
d-i finish-install/reboot_in_progress note
d-i pkgsel/include string rng-tools \
                          btrfs-tools \
                          openssh-client \
                          dbus \
                          debathena-transform-lighttpd \
                          gnupg2 \
% for p in elbe_initvm_packagelist:
                          ${p}=${elbe_version}* \
% endfor
% for n in pkgs:
% if n.tag == "pkg":
 ${pkg2preseed (n)}\
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
