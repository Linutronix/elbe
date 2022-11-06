# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2014, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import filecmp

from optparse import OptionParser


def walk_generated(gen_path, fix_path, exclude):

    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-branches

    file_to_rm = []
    file_differ = []
    gen_path = gen_path.rstrip("/")
    fix_path = fix_path.rstrip("/")

    for root, _, files in os.walk(gen_path):
        if root == gen_path:
            infs_root = "/"
        else:
            infs_root = root.replace(gen_path, "")

        if True in [infs_root.startswith(x) for x in exclude]:
            continue

        if not files:
            if not os.path.exists(fix_path + infs_root):
                print(f"empty directory {infs_root} only exists in gen image")
                file_to_rm.append(infs_root)
        else:
            for f in files:
                gen_fname = os.path.join(gen_path + infs_root, f)
                fix_fname = os.path.join(fix_path + infs_root, f)

                if os.path.exists(gen_fname) and os.path.exists(fix_fname):
                    if os.path.isfile(gen_fname) and os.path.isfile(fix_fname):
                        if not os.path.islink(
                                gen_fname) and not os.path.islink(fix_fname):
                            if not filecmp.cmp(
                                    gen_fname, fix_fname, shallow=False):
                                print(
                                    f"files {gen_fname} and {fix_fname} differ")
                                file_differ.append(os.path.join(infs_root, f))
                        else:
                            if not (os.readlink(gen_fname) ==
                                    os.readlink(fix_fname)):
                                print(
                                    f"symlinks {gen_fname} and "
                                    f"{fix_fname} differ")
                                file_differ.append(os.path.join(infs_root, f))

                elif not os.path.exists(gen_fname) and \
                        os.path.exists(fix_fname):
                    print(f"file {fix_fname} only exists in fixed image")
                elif os.path.exists(gen_fname) and not \
                        os.path.exists(fix_fname):
                    print(f"file {gen_fname} only exists in gen image")
                    file_to_rm.append(os.path.join(infs_root, f))

    return file_differ, file_to_rm


def walk_fixed(gen_path, fix_path, exclude):

    file_only = []
    dir_to_create = []
    gen_path = gen_path.rstrip("/")
    fix_path = fix_path.rstrip("/")

    for root, _, files in os.walk(fix_path):
        if root == fix_path:
            infs_root = "/"
        else:
            infs_root = root.replace(fix_path, "")

        if True in [infs_root.startswith(x) for x in exclude]:
            continue

        if not files:
            if not os.path.exists(gen_path + infs_root):
                print(f"empty directory {infs_root} only exists in fix image")
                dir_to_create.append(infs_root.lstrip("/"))
        else:
            for f in files:
                gen_fname = os.path.join(gen_path + infs_root, f)
                fix_fname = os.path.join(fix_path + infs_root, f)

                if not os.path.exists(gen_fname) and os.path.exists(fix_fname):
                    print(f"file {fix_fname} only exists in fixed image")
                    file_only.append(os.path.join(infs_root, f))

    return file_only, dir_to_create


def run_command(argv):

    oparser = OptionParser(usage="usage: %prog diff [options] <dir1> <dir2>")
    oparser.add_option("--exclude", action="append", dest="exclude",
                       help="Paths to exclude")
    (opt, args) = oparser.parse_args(argv)

    if len(args) != 2:
        print("Wrong number of arguments")
        oparser.print_help()
        sys.exit(20)

    if opt.exclude is None:
        opt.exclude = []

    gen_rfs = args[0]
    fix_rfs = args[1]

    differ, rm = walk_generated(gen_rfs, fix_rfs, opt.exclude)
    only, mkdir = walk_fixed(gen_rfs, fix_rfs, opt.exclude)

    print("suggesting:")
    print()

    for f in rm:
        print(f"<rm>{f}</rm>")

    for d in mkdir:
        print(f"<mkdir>{d}</mkdir>")

    print("")

    for f in differ + only:
        print(f"tar rf archive.tar -C {fix_rfs} {f}")
