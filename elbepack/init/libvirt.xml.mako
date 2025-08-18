## ELBE - Debian Based Embedded Rootfilesystem Builder
## SPDX-License-Identifier: GPL-3.0-or-later
## SPDX-FileCopyrightText: 2017-2018 Linutronix GmbH

<%
# TODO: Add dynamic name support
# TODO: Relativ file path for diskimage


import os
import shutil
from elbepack.filesystem import size_to_int
from elbepack.uuid7 import uuid7

# Generate UUID
uid = uuid7()

cpus = int(prj.text('max-cpus', default=defs, key='max-cpus'))
memory = size_to_int(prj.text('mem', default=defs, key='mem')) // 1024

imagetype = prj.text('img', default=defs, key='img')
img = os.path.join(directory, 'initvm.img')
img_base = os.path.join(directory, 'initvm-base.img')

emulator = shutil.which(prj.text('interpreter', default=defs, key='interpreter'))
nicmac = prj.text('buildimage/NIC/MAC', default=defs, key='nicmac')
forward = ''
for f in prj.node("portforwarding"):
    forward += ',hostfwd=%s::%s-:%s' % (
        f.text("proto"), f.text("host"), f.text("buildenv"))

forward += ',hostfwd=%s::%s-:%s' % ("tcp", soapport, "7588")
if sshport != -1:
    forward += ',hostfwd=%s::%s-:%s' % ("tcp", sshport, "22")

%><domain type='qemu'
xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
<name>${initvm_domain}</name>
<uuid>${uid}</uuid>
  <memory unit='KiB'>${memory}</memory>
  <currentMemory unit='KiB'>${memory}</currentMemory>
  <vcpu placement='static'>${cpus}</vcpu>
  <cpu mode='host-model' check='partial'>
    <model fallback='allow'/>
  </cpu>
  <os>
    <type arch='x86_64' machine='pc'>hvm</type>
  </os>
  <features>
    <acpi />
    <pae />
  </features>
  <clock offset='utc' />
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>${emulator}</emulator>
    <controller type='pci' index='0' model='pci-root' />
    <input type='mouse' bus='ps2' />
    <input type='keyboard' bus='ps2' />
    <rng model='virtio'>
      <backend model='random' />
    </rng>
    <memballoon model='none' />
    <disk type='file' device='disk'>
    <driver name='qemu' type='${imagetype}' />
    <source file='${img}' fdgroup='initvm.img' />
      <target dev='vda' bus='virtio' />
      <backingStore type='file'>
        <format type='qcow2'/>
        <source file='${img_base}' fdgroup='initvm-base.img'/>
        <backingStore/>
      </backingStore>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07'
      function='0x0' />
    </disk>
    <console type='pty'>
      <target type='serial' port='0' />
    </console>
  </devices>
  <qemu:commandline>
    <qemu:arg value='-netdev' />
    <qemu:arg value='user,id=user.0${forward}' />
    <qemu:arg value='-device' />
    <qemu:arg value='virtio-net-pci,netdev=user.0,mac=${nicmac},addr=05' />
  </qemu:commandline>
</domain>
