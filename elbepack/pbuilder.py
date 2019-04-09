# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015-2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2016 John Ogness <john.ogness@linutronix.de>
# Copyright (c) 2017 Kurt Kanzenbach <kurt@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import urllib2


def pbuilder_write_config(builddir, xml, _log):
    distname = xml.prj.text('suite')
    pbuilderrc_fname = os.path.join(builddir, "pbuilderrc")
    fp = open(pbuilderrc_fname, "w")

    fp.write('#!/bin/sh\n')
    fp.write('set -e\n')
    fp.write('MIRRORSITE="%s"\n' % xml.get_primary_mirror(False))
    fp.write(
        'OTHERMIRROR="deb http://127.0.0.1:8080%s/repo %s main"\n' %
        (builddir, distname))
    fp.write('BASETGZ="%s"\n' % os.path.join(builddir, 'pbuilder', 'base.tgz'))

    fp.write('DISTRIBUTION="%s"\n' % distname)

    fp.write(
        'BUILDRESULT="%s"\n' %
        os.path.join(
            builddir,
            'pbuilder',
            'result'))
    fp.write(
        'APTCACHE="%s"\n' %
        os.path.join(
            builddir,
            'pbuilder',
            'aptcache'))
    fp.write('HOOKDIR="%s"\n' % os.path.join(builddir, 'pbuilder', 'hooks.d'))
    fp.write('PATH="/usr/share/elbe/qemu-elbe:$PATH"\n')

    if xml.text("project/arch", key="arch") != 'amd64':
        fp.write('ARCHITECTURE="%s"\n' %
                 xml.text("project/buildimage/arch", key="arch"))
        fp.write('DEBOOTSTRAP="qemu-debootstrap"\n')
        fp.write('DEBOOTSTRAPOPTS=("${DEBOOTSTRAPOPTS[@]}" '
                 '"--arch=$ARCHITECTURE")\n')

    if xml.prj.has('noauth'):
        fp.write(
            'DEBOOTSTRAPOPTS=("${DEBOOTSTRAPOPTS[@]}" "--no-check-gpg")\n')
        fp.write('export ALLOWUNTRUSTED="yes"\n')

    # aptitude segfaults with armhf changeroots, great! :)
    # link: https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=834990
    fp.write('PBUILDERSATISFYDEPENDSCMD='
             '/usr/lib/pbuilder/pbuilder-satisfydepends-experimental\n')

    fp.close()


def pbuilder_write_apt_conf(builddir, xml):

    # writing apt.conf is only necessary, when we have noauth
    # return when its not set
    if not xml.prj.has('noauth'):
        return

    # noauth is set
    # create pbuilder/aptconfdir/apt.conf.d/16allowuntrusted
    aptconf_dir = os.path.join(builddir, "aptconfdir", "apt.conf.d")
    fp = open(os.path.join(aptconf_dir, "16allowuntrusted"), "w")

    # Make apt-get use --force-yes which is not specified by
    # pbuilder-satisfy-depends
    fp.write('APT::Get::force-yes "true";\n')

    # Also for safety add this:
    fp.write('APT::Get::AllowUnauthenticated "true";\n')

    # Make aptitude install untrusted packages without asking
    fp.write('Aptitude::CmdLine::Ignore-Trust-Violations "true";\n')
    fp.close()


def mirror_script_add_key(mirror, key_url):
    key_url = key_url.replace("LOCALMACHINE", "10.0.2.2")
    key_conn = urllib2.urlopen(key_url, None, 10)
    key_text = key_conn.read()
    key_conn.close()

    mirror += "cat << EOF | apt-key add -\n"
    mirror += key_text + "\n"
    mirror += "EOF\n"

    return mirror


def pbuilder_write_repo_hook(builddir, xml):

    pbuilder_hook_dir = os.path.join(builddir, "pbuilder", "hooks.d")

    fp = open(os.path.join(pbuilder_hook_dir, "G10elbe_apt_sources"), "w")

    if xml.prj is None:
        return "# No Project"

    if not xml.prj.has("mirror") and not xml.prj.has("mirror/cdrom"):
        return "# no mirrors configured"

    mirror = "#!/bin/sh\n"

    mirror += 'echo "deb http://127.0.0.1:8080' + builddir + '/repo ' + \
        xml.prj.text("suite") + ' main" > /etc/apt/sources.list\n'

    mirror = mirror_script_add_key(
        mirror,
        'http://127.0.0.1:8080' +
        builddir +
        '/repo/repo.pub')

    if xml.prj.has("mirror/primary_host"):
        mirror += 'echo "deb ' + xml.get_primary_mirror(None) + ' ' + \
                  xml.prj.text("suite") + ' main" >> /etc/apt/sources.list\n'

        if xml.prj.has("mirror/url-list"):
            for url in xml.prj.node("mirror/url-list"):
                if url.has("binary"):
                    mirror += 'echo "deb ' + url.text("binary").strip() + \
                              '" >> /etc/apt/sources.list\n'
                if url.has("key"):
                    key_url = url.text("key").strip()
                    mirror = mirror_script_add_key(mirror, key_url)

    if xml.prj.has("mirror/cdrom"):
        mirror += 'echo "deb copy:///cdrom/targetrepo %s main added" >> ' \
                  '/etc/apt/sources.list' % (xml.prj.text("suite"))

    mirror += 'apt-get update\n'
    mirror = mirror.replace("LOCALMACHINE", "10.0.2.2")

    fp.write(mirror)
    fp.close()
