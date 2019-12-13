## ELBE - Debian Based Embedded Rootfilesystem Builder
## Copyright (c) 2017 Philipp Arras <philipp.arras@linutronix.de>
## Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
## Copyright (c) 2018 Troben Hohn <torben.hohn@linutronix.de>
##
## SPDX-License-Identifier: GPL-3.0-or-later
##
<%
# TODO: Add dynamic name support
# TODO: Relativ file path for diskimage


import uuid
import multiprocessing
import os
from elbepack.filesystem import size_to_int

# Generate UUID
uid = uuid.uuid4()

name = cfg['initvm_domain']
cpus = int(prj.text('max-cpus', default=defs, key='max-cpus'))
cpus = min(multiprocessing.cpu_count(), cpus)
memory = size_to_int(prj.text('mem', default=defs, key='mem')) // 1024

imagetype = prj.text('img', default=defs, key='img')
img = os.path.join(opt.directory, 'buildenv.img')

emulator = prj.text('interpreter', default=defs, key='interpreter')
nicmac = prj.text('buildimage/NIC/MAC', default=defs, key='nicmac')
forward = ''
for f in prj.node("portforwarding"):
    forward += ',hostfwd=%s::%s-:%s' % (
        f.text("proto"), f.text("host"), f.text("buildenv"))

forward += ',hostfwd=%s::%s-:%s' % ("tcp", cfg['soapport'], "7588")
if cfg['sshport'] != '-1':
    forward += ',hostfwd=%s::%s-:%s' % ("tcp", cfg['sshport'], "22")

%><domain type='kvm'
xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
<name>${name}</name>
<uuid>${uid}</uuid>
  <memory unit='KiB'>${memory}</memory>
  <currentMemory unit='KiB'>${memory}</currentMemory>
  <vcpu placement='static'>${cpus}</vcpu>
% if opt.nesting:
  <cpu mode='host-model' check='partial'>
    <model fallback='allow'/>
  </cpu>
% endif
  <os>
    <type arch='x86_64' machine='${machine_type}'>hvm</type>
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
    <controller type='usb' index='0' />
    <controller type='pci' index='0' model='pci-root' />
    <input type='mouse' bus='ps2' />
    <input type='keyboard' bus='ps2' />
    <graphics type='spice' autoport='yes' />
    <video>
      <model type='cirrus' vram='9216' heads='1' />
    </video>
    <rng model='virtio'>
      <backend model='random' />
    </rng>
    <memballoon model='none' />
    <disk type='file' device='disk'>
    <driver name='qemu' type='${imagetype}' />
    <source file='${img}' />
      <target dev='vda' bus='virtio' />
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07'
      function='0x0' />
    </disk>
    <console type='pty'>
      <target type='serial' port='0' />
    </console>
    <channel type='spicevmc'>
      <target type='virtio' name='com.redhat.spice.0' />
      <address type='virtio-serial' controller='0' bus='0'
      port='1' />
    </channel>
  </devices>
  <qemu:commandline>
    <qemu:arg value='-netdev' />
    <qemu:arg value='user,id=user.0${forward}' />
    <qemu:arg value='-device' />
    <qemu:arg value='virtio-net-pci,netdev=user.0,mac=${nicmac}' />
  </qemu:commandline>
</domain>
