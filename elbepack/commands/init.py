# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2015, 2017, 2018 Linutronix GmbH

import os
import sys
import shutil
import logging

from optparse import OptionParser

from elbepack.treeutils import etree
from elbepack.validate import validate_xml
from elbepack.debinstaller import copy_kinitrd, NoKinitrdException
from elbepack.xmldefaults import ElbeDefaults
from elbepack.version import elbe_version
from elbepack.templates import write_template, get_initvm_preseed
from elbepack.directories import init_template_dir, elbe_dir
from elbepack.config import cfg
from elbepack.shellhelper import system, do, system_out
from elbepack.log import elbe_logging
from elbepack.filesystem import Filesystem


def run_command(argv):

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    oparser = OptionParser(usage="usage: %prog init [options] <filename>")

    oparser.add_option("--skip-validation", action="store_true",
                       dest="skip_validation", default=False,
                       help="Skip xml schema validation")

    oparser.add_option("--directory", dest="directory", default="./build",
                       help="Working directory (default is build)",
                       metavar="FILE")

    oparser.add_option(
        "--cdrom",
        dest="cdrom",
        help="Use FILE as cdrom iso, and use that to build the initvm",
        metavar="FILE")

    oparser.add_option("--buildtype", dest="buildtype",
                       help="Override the buildtype")

    oparser.add_option(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="start qemu in graphical mode to enable console switch")

    oparser.add_option(
        "--devel",
        dest="devel",
        action="store_true",
        default=False,
        help="use devel mode, and install current builddir inside initvm")

    oparser.add_option(
        "--nesting",
        dest="nesting",
        action="store_true",
        default=False,
        help="allow initvm to support nested kvm. "
             "This makes /proc/cpuinfo inside initvm differ per host.")

    oparser.add_option(
        "--skip-build-bin",
        action="store_false",
        dest="build_bin",
        default=True,
        help="Skip building Binary Repository CDROM, for exact Reproduction")

    oparser.add_option(
        "--skip-build-sources",
        action="store_false",
        dest="build_sources",
        default=True,
        help="Skip building Source CDROM")

    (opt, args) = oparser.parse_args(argv)

    if not args:
        print("no filename specified")
        oparser.print_help()
        sys.exit(20)
    elif len(args) > 1:
        print("too many filenames specified")
        oparser.print_help()
        sys.exit(20)

    with elbe_logging({"files": None}):
        if opt.devel:
            if not os.path.isdir(os.path.join(elbe_dir, "elbepack")):
                logging.error("Devel Mode only valid, "
                              "when running from elbe checkout")
                sys.exit(20)

        if not opt.skip_validation:
            validation = validate_xml(args[0])
            if validation:
                logging.error("xml validation failed. Bailing out")
                for i in validation:
                    logging.error(i)
                sys.exit(20)

        xml = etree(args[0])

        if not xml.has("initvm"):
            logging.error("fatal error: "
                          "xml missing mandatory section 'initvm'")
            sys.exit(20)

        if opt.buildtype:
            buildtype = opt.buildtype
        elif xml.has("initvm/buildtype"):
            buildtype = xml.text("/initvm/buildtype")
        else:
            buildtype = "nodefaults"

        defs = ElbeDefaults(buildtype)

        http_proxy = xml.text("/initvm/mirror/primary_proxy", default="")
        http_proxy = http_proxy.strip().replace("LOCALMACHINE", "localhost")

        if opt.cdrom:
            mirror = xml.node("initvm/mirror")
            mirror.clear()
            cdrom = mirror.ensure_child("cdrom")
            cdrom.set_text(os.path.abspath(opt.cdrom))

        try:
            os.makedirs(opt.directory)
        except OSError as e:
            logging.error("unable to create project directory: %s (%s)",
                          opt.directory,
                          e.strerror)
            sys.exit(30)

        out_path = os.path.join(opt.directory, ".elbe-in")
        try:
            os.makedirs(out_path)
        except OSError as e:
            logging.error("unable to create subdirectory: %s (%s)",
                          out_path,
                          e.strerror)
            sys.exit(30)

        initvm_http_proxy = http_proxy.replace('http://localhost:',
                                               'http://10.0.2.2:')
        d = {"elbe_version": elbe_version,
             "defs": defs,
             "opt": opt,
             "xml": xml,
             "prj": xml.node("/initvm"),
             "http_proxy": initvm_http_proxy,
             "pkgs": xml.node("/initvm/pkg-list") or [],
             "preseed": get_initvm_preseed(xml),
             "cfg": cfg}

        if http_proxy != "":
            os.putenv("http_proxy", http_proxy)
            os.putenv("https_proxy", http_proxy)
            os.putenv("no_proxy", "localhost,127.0.0.1")

        try:
            copy_kinitrd(xml.node("/initvm"), out_path)
        except NoKinitrdException as e:
            msg = str(e)
            logging.error("Failure to download kernel/initrd debian Package:")
            logging.error("")
            logging.error(msg)
            logging.error("")
            logging.error("Check Mirror configuration")
            if 'SHA256SUMS' in msg:
                logging.error("If you use debmirror please read "
                              "https://github.com/Linutronix/elbe/issues/188 "
                              "on how to work around the issue")
            sys.exit(20)

        templates = os.listdir(init_template_dir)

        make_executable = ["init-elbe.sh.mako",
                           "preseed.cfg.mako"]

        for t in templates:
            o = t.replace(".mako", "")

            if t in ("Makefile.mako", "libvirt.xml.mako"):
                write_template(
                    os.path.join(
                        opt.directory, o), os.path.join(
                        init_template_dir, t), d, linebreak=True)
            else:
                write_template(
                    os.path.join(
                        out_path, o), os.path.join(
                        init_template_dir, t), d, linebreak=False)

            if t in make_executable:
                os.chmod(os.path.join(out_path, o), 0o755)

        shutil.copyfile(args[0],
                        os.path.join(out_path, "source.xml"))


        keys = []
        for key in xml.all(".//initvm/mirror/url-list/url/raw-key"):
            keys.append(key.et.text)

        if opt.cdrom:
            keys.append(system_out(f'7z x -so "{opt.cdrom}" repo.pub'))

        import_keyring = os.path.join(out_path, "elbe-keyring")

        do(f'gpg --no-options \
                 --no-default-keyring \
                 --keyring {import_keyring} --import',
           stdin="".join(keys).encode('ascii'),
           allow_fail=True,
           env_add={'GNUPGHOME': out_path})

        export_keyring = import_keyring + ".gpg"

        # No need to set GNUPGHOME because both input and output
        # keyring files are specified.

        do(f'gpg --no-options \
                --no-default-keyring \
                --keyring {import_keyring} \
                --export \
                --output {export_keyring}')

        if opt.devel:
            out_real = os.path.realpath(out_path)
            opts = []
            if out_real.startswith(elbe_dir + os.sep):
                opts.append(
                    f'--exclude "{os.path.relpath(out_path, start=elbe_dir)}"')

            opts.append("--exclude-vcs")
            opts.append("--exclude-vcs-ignores")
            opts.append("--exclude='elbe-build*'")
            opts.append("--exclude='docs/*'")
            tar_fname = os.path.join(out_path, "elbe-devel.tar.bz2")
            system(f'tar cfj "{tar_fname}" {" ".join(opts)} -C "{elbe_dir}" .')

        to_cpy = [("apt.conf", "etc/apt"),
                  ("init-elbe.sh", ""),
                  ("source.xml", ""),
                  ("initrd-cdrom.gz", ""),
                  ("vmlinuz", ""),
                  ("preseed.cfg", "")]

        elbe_in  = Filesystem(out_path)

        if opt.devel:
            to_cpy.append(("elbe-devel.tar.bz2", ""))

        # Convert relative rfs path to absolute in the system
        to_cpy = [(elbe_in.fname(src), elbe_in.fname(os.path.join("initrd-tree", dst)))
                  for src, dst
                  in to_cpy]

        # These are already absolute path!
        keyrings = elbe_in.fname(os.path.join("initrd-tree", "usr/share/keyrings"))
        for gpg in elbe_in.glob("*.gpg"):
            to_cpy.append((gpg, keyrings))

        for src, dst in to_cpy:
            try:
                os.makedirs(dst)
            except FileExistsError:
                pass
            shutil.copy(src, dst)
