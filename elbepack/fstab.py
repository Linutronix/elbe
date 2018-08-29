# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2013-2014, 2017 Manuel Traut <manut@linutronix.de>
# Copyright (c) 2014, 2017 Torben Hohn <torben.hohn@linutronix.de>
# Copyright (c) 2015 Matthias Buehler <matthias.buehler@de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os


def get_mtdnum(xml, label):
    tgt = xml.node("target")
    if not tgt.has("images"):
        raise Exception("No images tag in target")

    for i in tgt.node("images"):
        if i.tag != "mtd":
            continue

        if not i.has("ubivg"):
            continue

        for v in i.node("ubivg"):
            if v.tag != "ubi":
                continue

            if v.text("label") == label:
                return i.text("nr")

    raise Exception("No ubi volume with label " + label + " found")


def get_devicelabel(xml, node):
    if node.text("fs/type") == "ubifs":
        return "ubi %s:%s" % (get_mtdnum(xml, node.text("label")),
                              node.text("label"))

    return "LABEL=" + node.text("label")


class mountpoint_dict (dict):
    def __init__(self):
        dict.__init__(self)
        self.id_count = 0

    def register(self, fstabentry):
        mp = fstabentry.mountpoint

        if mp in self:
            fstabentry.id = self[mp].id
        else:
            fstabentry.id = str(self.id_count)
            self[mp] = fstabentry
            self.id_count += 1

    @staticmethod
    def mountdepth(mp):
        depth = 0

        while True:
            mp, t = os.path.split(mp)
            if t == '':
                return depth
            depth += 1

    def depthlist(self):
        mplist = sorted(self.keys(), key=mountpoint_dict.mountdepth)

        return [self[x] for x in mplist]


class fstabentry(object):

    # pylint: disable=too-many-instance-attributes

    def __init__(self, xml, entry, id=0):
        if entry.has("source"):
            self.source = entry.text("source")
        else:
            self.source = get_devicelabel(xml, entry)

        if entry.has("label"):
            self.label = entry.text("label")

        self.mountpoint = entry.text("mountpoint")
        self.options = entry.text("options", default="defaults")
        if entry.has("fs"):
            self.fstype = entry.text("fs/type")
            self.mkfsopt = entry.text("fs/mkfs", default="")
            self.passno = entry.text("fs/passno", default="0")

        # These attributes are filled later
        # using set_geometry()
        self.size = 0
        self.offset = 0
        self.filename = ''
        self.partnum = 0
        self.number = ''

        self.id = str(id)

    def get_str(self):
        return "%s %s %s %s 0 %s\n" % (self.source, self.mountpoint,
                                       self.fstype, self.options, self.passno)

    def mountdepth(self):
        h = self.mountpoint
        depth = 0

        while True:
            h, t = os.path.split(h)
            if t == '':
                return depth
            depth += 1

    def get_label_opt(self):
        if self.fstype == "ext4":
            return "-L " + self.label
        if self.fstype == "ext2":
            return "-L " + self.label
        if self.fstype == "ext3":
            return "-L " + self.label
        if self.fstype == "vfat":
            return "-n " + self.label
        if self.fstype == "xfs":
            return "-L " + self.label
        if self.fstype == "btrfs":
            return "-L " + self.label

        return ""

    def set_geometry(self, ppart, disk):
        sector_size = 512
        self.offset = ppart.geometry.start * sector_size
        self.size = ppart.getLength() * sector_size
        self.filename = disk.device.path
        self.partnum = ppart.number
        self.number = '{}{}'.format(disk.type, ppart.number)

    def losetup(self, outf, loopdev):
        outf.do('losetup -o%d --sizelimit %d /dev/%s "%s"' %
                (self.offset, self.size, loopdev, self.filename))
