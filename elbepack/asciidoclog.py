# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014, 2016 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2014 Ferdinand Schwenk <ferdinand.schwenk@emtrion.de>
# Copyright (c) 2014, 2016-2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

from elbepack.shellhelper import CommandError, command_out_stderr, command_out


class LogBase(object):
    def __init__(self, fp):
        self.fp = fp

    def printo(self, text=""):
        self.fp.write("%s\n" % str(text))

    def print_raw(self, text):
        self.fp.write(text)

    def h1(self, text):
        self.printo()
        self.printo(text)
        self.printo("=" * len(str(text)))
        self.printo()

    def h2(self, text):
        self.printo()
        self.printo(text)
        self.printo("-" * len(str(text)))
        self.printo()

    def table(self):
        self.printo("|=====================================")

    def verbatim_start(self):
        self.printo("---------------------------------------"
                    "---------------------------------------")

    def verbatim_end(self):
        self.printo("---------------------------------------"
                    "---------------------------------------")
        self.printo()

    def do(self, cmd, allow_fail=False, stdin=None, env_add=None):

        if stdin is None:
            self.printo("running cmd +%s+" % cmd)
        else:
            self.printo("running cmd +%s with STDIN %s+" % (cmd, stdin))

        self.verbatim_start()
        ret, _ = command_out(cmd, stdin=stdin, output=self.fp, env_add=env_add)
        self.verbatim_end()

        if ret != 0:
            self.printo("Command failed with errorcode %d" % ret)
            if not allow_fail:
                raise CommandError(cmd, ret)

    def chroot(self, directory, cmd, **args):
        os.environ["LANG"] = "C"
        os.environ["LANGUAGE"] = "C"
        os.environ["LC_ALL"] = "C"

        chcmd = "chroot %s %s" % (directory, cmd)
        self.do(chcmd, **args)

    def get_command_out(self, cmd, allow_fail=False):

        self.printo("getting output from cmd +%s+" % cmd)

        ret, output, stderr = command_out_stderr(cmd)

        if stderr:
            self.verbatim_start()
            self.print_raw(stderr)
            self.verbatim_end()

        if ret != 0:
            self.printo("Command failed with errorcode %d" % ret)
            if not allow_fail:
                raise CommandError(cmd, ret)

        return output


class ASCIIDocLog (LogBase):
    def __init__(self, fname, append=False):
        self.fname = fname
        if append:
            fp = file(fname, "a", 0)
        else:
            if os.path.isfile(fname):
                os.unlink(fname)
            fp = file(fname, "w", 0)

        LogBase.__init__(self, fp)

    def reset(self):
        self.fp.close()
        if os.path.isfile(self.fname):
            os.unlink(self.fname)
        self.fp = file(self.fname, "w", 0)


class StdoutLog(LogBase):
    def __init__(self):
        LogBase.__init__(self, sys.stdout)

    def reset(self):
        pass


class StderrLog(LogBase):
    def __init__(self):
        LogBase.__init__(self, sys.stderr)

    def reset(self):
        pass
