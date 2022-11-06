# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2020 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import logging
import optparse
import os
import shutil
import tempfile
import traceback

import pexpect

from elbepack.directories import elbe_exe
from elbepack.log import elbe_logging
from elbepack.treeutils import etree
from elbepack.shellhelper import get_command_out, command_out, do, CommandError
from elbepack.filesystem import TmpdirFilesystem

DEVNULL = open(os.devnull, "w")

def run_command(argv):

    oparser = optparse.OptionParser(usage="usage: %prog check-build <cmd> <build-dir>")

    (_, args) = oparser.parse_args(argv)

    if len(args) < 2:
        oparser.print_help()
        os.sys.exit(20)

    if args[0] == "all":
        tests = [CheckBase.tests[tag] for tag in CheckBase.tests]
    elif args[0] in CheckBase.tests:
        tests = [CheckBase.tests[args[0]]]
    else:
        print(f"Invalid check test {args[0]}")
        print("Valid tests are:\n\tall")
        for tag in CheckBase.tests:
            print(f"\t{tag}")
        os.sys.exit(20)

    total_cnt = 0
    fail_cnt  = 0

    with elbe_logging({"streams":None}):

        for test in tests:

            logging.info("Starting test %s (%s)", test.__name__, test.__doc__)
            os.chdir(args[1])
            ret = test()()

            total_cnt += 1
            if ret:
                fail_cnt += 1
                logging.error("FAILED test %s (%s)", test.__name__, test.__doc__)

        logging.info("Passed %d tests ouf of %d",
                     total_cnt - fail_cnt, total_cnt)

    os.sys.exit(fail_cnt)

class CheckException(Exception):
    pass

class CheckBase:

    tests = dict()

    def __init__(self):
        self.ret = 0

    def __call__(self):
        try:
            self.ret = self.run()
        except CheckException as E:
            logging.exception(E)
            self.ret = 1
        except: # pylint: disable=bare-except
            logging.error(traceback.format_exc())
            self.ret = 1
        return self.ret

    @classmethod
    def register(cls, tag):
        def _register(test):
            cls.tests[tag] = test
            return test
        return _register

    # pylint: disable=no-self-use
    def run(self):
        raise Exception("Check run method not implemented")
        # pylint: disable=unreachable
        return 0

    def fail(self, reason):
        raise CheckException(reason)

@CheckBase.register("cdrom")
class CheckCdroms(CheckBase):

    """Check for cdroms integrity"""

    def extract_cdrom(self, tgt, cdrom):
        try:
            do(f'7z x -o"{tgt}" "{cdrom}"')
        except CommandError as E:
            self.fail(f"Failed to extract cdrom {cdrom}:\n{E}")

    def dpkg_get_infos(self, path, fmt):
        """Get dpkg infos for .deb and .dsc file formats"""
        try:
            if path.endswith(".deb"):
                cmd = f'dpkg -f "{path}" {" ".join(fmt)}'
            elif path.endswith(".dsc"):
                cmd = f'grep -E "^({"|".join(fmt)}):" {path}'
            return get_command_out(cmd).decode("utf-8")
        except CommandError as E:
            self.fail(
                f"Failed to get debian infos ({'|'.join(fmt)}) "
                f"for {path}:\n{E}")

    @staticmethod
    def cmp_version(v1, v2):
        return command_out(
            f"dpkg --compare-versions {v1} eq {v2}", output=DEVNULL)[0]

    def do_src(self, sources, src_total):
        """Check for sources in src-cdrom*"""

        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches

        iso_it  = glob.iglob("src-cdrom*")
        src_cnt = 0

        # For every src-cdrom*, extract it to a temporary directory
        # and find all *.dsc files
        for cdrom in iso_it:
            with TmpdirFilesystem() as tmp:
                self.extract_cdrom(tmp.path, cdrom)
                for _, realpath in tmp.walk_files():
                    if not realpath.endswith('.dsc'):
                        continue

                    infos = self.dpkg_get_infos(realpath,
                                                ["Source", "Version"])
                    src_name    = None
                    src_version = None

                    for info in infos.split('\n'):

                        if info.startswith("Source:"):
                            src_name = info.split('Source:')[1].strip(' ')

                        # Same as for the binary version.  The
                        # PGP's signature contains a version field
                        elif info.startswith("Version:"):
                            if not src_version:
                                src_version = info.split('Version:')[1].strip(' ')

                    if src_name in sources:

                        match = False

                        for version in sources[src_name]:

                            # Found a matching version; prune it
                            if self.cmp_version(version, src_version) == 0:

                                logging.info("Validating source %s_%s",
                                             src_name, version)

                                sources[src_name].remove(version)
                                src_cnt += 1
                                match   = True

                                break

                        # NOTE! - Because the way the source table is
                        # generated, it's not possible to have multiple time
                        # the same version of a source (you have different
                        # versions only).  However, this is totally possible
                        # for cdrom because of multiple components.  Thus,
                        # whenever the source table can handle per component
                        # sources, this case should emit an error instead of
                        # a warning
                        if not match:
                            logging.warning("Can't find matching version for source %s_%s.\n"
                                            "It might have already been validated",
                                            src_name, src_version)
                    else:
                        logging.error("Extra source %s_%s found",
                                      src_name, src_version)
                        self.ret = 1

        # List missing sources
        for src_name in sources:
            for src_version in sources[src_name]:
                logging.error("Missing source %s_%s",
                              src_name, src_version)

        logging.info("Succesfully validated %d source packages out of %d",
                     src_cnt, src_total)

        if src_cnt != src_total:
            self.ret = 1

    def do_bin(self):
        """Check for binaries in bin-cdrom*.

        Return a tuple of the form ({ "source-name" : [versions ..] }, src_cnt).

        Put in other words, validating binary cdroms will give us back a
        dictionnary where the keys are the source package's name, and the values
        of these keys are lists of versions.  It will also return a total count
        of source that is in the dictionnary.
        """

        # NOTE! - The binary table should be okay with the current
        # bin-cdrom.iso.  However, the way that the source table is genrated is
        # not okay for now.  Indeed, it's not aware of components.  So for
        # example, if two components have a binary in common, they will share
        # the corresponding source in the source table.  The solution is not as
        # trivial as having a reference counter or appending to a list, because
        # a component could have multiple binaries that match to the same source
        # package.  Thus, the only way is to make the source table component
        # aware.

        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements

        # Every build has a source.xml where the list of binaries
        # installed can be found
        xml = etree("source.xml")

        # Initial statistics fo the build
        bin_cnt   = 0
        src_cnt   = 0
        bin_total = 0

        binaries = {}
        sources  = {}

        # Create a dictionnary of the form {"bin-name": [versions ..]}
        # from the source.xml.  We do this by iterating over all <pkg>
        for tag in xml.all("./*/pkg"):

            bin_pkg = tag.et.text

            # Package already in the dictionnary? Add its version.
            # Otherwise, add a new entry into the dictionnary
            if bin_pkg in binaries:
                binaries[bin_pkg].append(tag.et.attrib["version"])
            else:
                binaries[bin_pkg] = [tag.et.attrib["version"]]

            bin_total += 1

        # For every bin-cdrom, create a temporary directory where to
        # extract it and find all *.deb files
        #
        # pylint: disable=too-many-nested-blocks
        for cdrom in glob.glob("bin-cdrom*"):
            with TmpdirFilesystem() as tmp:
                self.extract_cdrom(tmp.path, cdrom)
                for _, realpath in tmp.walk_files():
                    if not realpath.endswith('.deb'):
                        continue

                    # Extract informations from .deb
                    infos    = self.dpkg_get_infos(realpath, ["Package",
                                                              "Source",
                                                              "Version",
                                                              "Built-Using"])
                    src_name    = None
                    src_version = None
                    bin_name    = None
                    bin_version = None

                    for line in infos.split('\n'):

                        # Package: <PACKAGE>
                        if line.startswith("Package:"):
                            bin_name = line.split('Package:')[1].strip(' \t')

                        # Version: <VERSION>
                        #
                        # Skip PGP's version.  The package version is
                        # supposed to be before the PGP signature.  However,
                        # the PGP signature will put a 'Version' field.
                        # Thus, let's check if we already have found a
                        # binary version and don't overwrite it
                        elif line.startswith("Version:"):
                            if not bin_version:
                                bin_version = line.split('Version:')[1].strip(' ')

                        # Source: <SOURCE> [(VERSION)]
                        #
                        # This field is optional.  If it is not present, the
                        # source package default to the bin package
                        elif line.startswith("Source:"):
                            src_infos = line.split('Source:')[1].strip(' ').split(' ')
                            src_name = src_infos[0]
                            if len(src_infos) > 1:
                                src_version = src_infos[1].strip("()")

                        # Built-Using: <SRC (=VERSION)>...
                        #
                        # Sources list in the built-using field are
                        # seperated by a comma
                        elif line.startswith("Built-Using:"):

                            built_using = line.split("Built-Using:")[1].strip(' ').split(',')

                            for src in built_using:

                                name, version = src.strip(' ').split(' ', 1)
                                version = version.strip("(= )")

                                # TODO - This is not component aware!
                                if name in sources:
                                    if version not in sources[name]:
                                        sources[name].add(version)
                                        src_cnt += 1
                                else:
                                    src_cnt += 1
                                    sources[name] = {version}


                    # No source was found
                    if src_name is None:
                        src_name    = bin_name
                        src_version = bin_version

                    # No source version was found
                    elif src_version is None:
                        src_version = bin_version

                    # TODO - This is not component aware!
                    #
                    # Let's build a dictionnary of sources of the form
                    # {"source-name" : [versions ..]}. Same as the binary
                    # dictionnary before
                    if src_name in sources:
                        if src_version not in sources[src_name]:
                            sources[src_name].add(src_version)
                            src_cnt += 1
                    else:
                        sources[src_name] = {src_version}
                        src_cnt += 1

                    # Prune version of this binary
                    bin_cnt += 1
                    try:
                        binaries[bin_name].remove(bin_version)
                        logging.info("Validating binary %s_%s",
                                     bin_name, bin_version)
                        logging.info("Adding source %s_%s", src_name, src_version)
                    except KeyError:
                        logging.error("Foreign binary found %s_%s",
                                      bin_name, bin_version)
                        self.ret = 1

        # List all missing binaries
        for bin_name in binaries:
            for bin_version in binaries[bin_name]:
                logging.error("Missing binary %s_%s", bin_name, bin_version)

        logging.info("Succesfully validated %d binary packages out of %d",
                     bin_cnt, bin_total)

        if bin_cnt != bin_total:
            self.ret = 1

        return sources, src_cnt

    def run(self):
        sources, src_cnt = self.do_bin()
        self.do_src(sources, src_cnt)
        return self.ret

@CheckBase.register("img")
class CheckImage(CheckBase):

    """Check if image can boot"""

    @staticmethod
    def open_tgz(path):
        tmp = tempfile.NamedTemporaryFile(prefix='elbe')
        command_out(
            f"tar --to-stdout --extract --gunzip --file {path}", output=tmp)
        return tmp

    def open_img(self, path):
        if path.endswith(".tar.gz"):
            return self.open_tgz(path)
        return open(path)

    def run(self):

        # pylint: disable=attribute-defined-outside-init
        self.xml = etree("source.xml")

        fail_cnt  = 0
        total_cnt = 0

        # For all image
        for tag in self.xml.all(".//check-image-list/check"):
            fail_cnt  += self.do_img(tag)
            total_cnt += 1

        logging.info("Succesfully validate %d images out of %d",
                     total_cnt - fail_cnt, total_cnt)

        return fail_cnt

    def do_img(self, tag):

        img_name = tag.text("./img")
        qemu     = tag.text("./interpreter")

        with self.open_img(img_name) as img:

            # ELBE_IMG always points to the opened image
            os.environ["ELBE_IMG"] = img.name

            opts = os.path.expandvars(tag
                                      .text("./interpreter-opts")
                                      .strip(' \t\n'))

            for candidate, action in [("login",  self.do_login),
                                      ("serial", self.do_serial)]:

                element = tag.et.find(os.path.join("./action", candidate))

                if element is not None:
                    return action(element, img_name, qemu, opts)

        # No valid action!
        return 1


    def do_login(self, _element, img_name, qemu, opts):

        passwd = "root"
        if self.xml.find(".//action/login").text:
            passwd = self.xml.find(".//action/login").text

        comm = [
            ("expect", ".*[Ll]ogin:.*"),
            ("sendline", "root"),
            ("expect", "[Pp]assword:.*"),
            ("sendline", passwd),
            ("expect", ".*#"),

            # This assume systemd is on the system.  We might want to change
            # this to a more generic way
            ("sendline", "shutdown --poweroff now bye"),

            ("expect", "bye"),

            # 30 seconds timeout for EOF; This will fail if systemd goes haywire
            ("EOF", ""),
        ]

        return self.do_comm(img_name, qemu, opts, comm)

    def do_serial(self, element, img_name, qemu, opts):

        comm = [(action.tag, action.et.text) for action in element]

        return self.do_comm(img_name, qemu, opts, comm)

    def do_comm(self, img_name, qemu, opts, comm):

        child      = pexpect.spawn(qemu + " " + opts)
        transcript = []
        ret        = 0

        try:
            for action, text in comm:

                if action == "expect":

                    # Try to expect something from the guest If there's a
                    # timeout; the test fails Otherwise; Add to the transcript
                    # what we received
                    try:
                        child.expect(text, timeout=60)
                    except pexpect.exceptions.TIMEOUT:
                        logging.error('Was expecting "%s" but got timeout (%ds)',
                                      text, child.timeout)
                        ret = 1
                        break
                    else:
                        transcript.append(child.before.decode('utf-8'))
                        transcript.append(child.after.decode('utf-8'))

                elif action == "sendline":
                    child.sendline(text)

                # We're expecting the serial line to be closed by the guest.  If
                # there's a timeout, it means that the guest has not closed the
                # line and the test has failed.  In every case the test ends
                # here.
                elif action == "EOF":
                    try:
                        child.expect(pexpect.EOF)
                    except pexpect.exceptions.TIMEOUT:
                        print(
                            'Was expecting EOF but got timeout '
                            f'({child.timeout})')
                        self.ret = 1
                    else:
                        transcript.append(child.before.decode('utf-8'))
                    break

        # Woops. The guest has die and we didn't expect that!
        except pexpect.exceptions.EOF as E:
            logging.error("Communication was interrupted unexpectedly %s", E)
            ret = 1

        child.close()

        logging.info("Transcript for image %s:\n"
                     "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
                     "%s\n"
                     "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
                     img_name, ''.join(transcript))

        return ret or child.exitstatus

@CheckBase.register("sdk")
class CheckSDK(CheckBase):
    """Check if SDK is working"""

    script = b"""
set -x

mkdir project

. $ELBE_SDK_ENV

cd project || exit 1

touch README

cat -> hello.c <<EOF
#include <stdio.h>
int main(void)
{
    printf("Hello World!");
    return 0;
}
EOF

cat -> configure.ac <<EOF
AC_INIT(hello,0.1)
AM_INIT_AUTOMAKE([foreign])
AC_PROG_CC
AC_CONFIG_FILES(Makefile)
AC_OUTPUT
EOF

cat -> Makefile.am <<EOF
bin_PROGRAMS  = hello
hello_SOURCES = hello.c
hello_LDFLAGS = -static
EOF

autoreconf -i

./configure ${CONFIGURE_FLAGS}

make
make install DESTDIR=./tmp

out=$(./hello)

if [ $? -eq 0 ] && [ "$out" = "Hello World!" ] ;
then
    exit 0
fi
exit 1
"""

    def do_sdk(self, sdk):

        with TmpdirFilesystem() as tmp:

            # Make a copy of the installer
            shutil.copyfile(sdk, tmp.fname(sdk))

            # Let's work in our temp dir from now on
            os.chdir(tmp.path)

            # The script is self extracting; it needs to be executable
            os.chmod(sdk, 0o744)

            # Extract here with 'yes' to all answers
            do(f"./{sdk} -y -d .")

            # Get environment file
            env = tmp.glob("environment-setup*")[0]

            # NOTE!  This script requires binfmt to be installed.
            do("/bin/sh", stdin=self.script, env_add={"ELBE_SDK_ENV": env})

    def run(self):
        for sdk in glob.glob("setup-elbe-sdk*"):
            self.do_sdk(sdk)

@CheckBase.register("rebuild")
class CheckRebuild(CheckBase):

    def run(self):
        do(f"{elbe_exe} initvm submit --skip-build-source bin-cdrom.iso")
