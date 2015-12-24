# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2013  Linutronix GmbH
#
# This file is part of ELBE.
#
# ELBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ELBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ELBE.  If not, see <http://www.gnu.org/licenses/>.

import os

def get_mtdnum(xml, label):
  tgt = xml.node ("target")
  if not tgt.has("images"):
    raise Exception( "No images tag in target" )

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

  raise Exception( "No ubi volume with label " + label + " found" )


def get_devicelabel( xml, node ):
  if node.text("fs/type") == "ubifs":
    return "ubi" + get_mtdnum(xml, node.text("label")) + ":" + node.text("label")
  else:
    return "LABEL=" + node.text("label")


class fstabentry(object):
    def __init__(self, xml, entry):
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
        if entry.has("passno"):
            self.passno = entry.text("passno")
        else:
            self.passno = "0"

    def get_str(self):
        return "%s %s %s %s 0 %s\n" % (self.source, self.mountpoint, self.fstype, self.options, self.passno)

    def mountdepth(self):
        h = self.mountpoint
        depth = 0

        while True:
            h, t = os.path.split(h)
            if t=='':
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

    def losetup( self, outf, loopdev ):
        outf.do( 'losetup -o%d --sizelimit %d /dev/%s "%s"' % (self.offset, self.size, loopdev, self.filename) )
