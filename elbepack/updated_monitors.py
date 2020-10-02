# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2015 Ferdinand Schwenk <ferdinand@ping.lan>
# Copyright (c) 2015, 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import threading
import pyinotify
import pyudev

from elbepack.updated import is_update_file, handle_update_file

# TODO:py3 Remove object inheritance
# pylint: disable=useless-object-inheritance
class UpdateMonitor(object):
    def __init__(self, status):
        self.status = status

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def join(self):
        raise NotImplementedError


if udev_available:
    def get_mountpoint_for_device(dev):
        with open("/proc/mounts") as f:
            for line in f:
                fields = line.split()
                try:
                    if fields[0] == dev:
                        return fields[1]
                except BaseException:
                    pass
            return None

    class USBMonitor (UpdateMonitor):
        def __init__(self, status, recursive=False):
            super(USBMonitor, self).__init__(status)
            self.recursive = recursive
            self.context = pyudev.Context()
            self.monitor = pyudev.Monitor.from_netlink(self.context)
            self.observer = pyudev.MonitorObserver(
                self.monitor, self.handle_event)

        def handle_event(self, action, device):
            if (action == 'add'
                and device.get('ID_BUS') == 'usb'
                    and device.get('DEVTYPE') == 'partition'):

                mnt = self.get_mountpoint_for_device(device.device_node)
                if not mnt:
                    self.status.log(
                        "Detected USB drive but it was not mounted.")
                    return

                for (dirpath, dirnames, filenames) in os.walk(mnt):
                    # Make sure we process the files in alphabetical order
                    # to get a deterministic behaviour
                    dirnames.sort()
                    filenames.sort()
                    for f in filenames:
                        upd_file = os.path.join(dirpath, f)
                        if is_update_file(upd_file):
                            self.status.log(
                                "Found update file '%s' on USB-Device." %
                                upd_file)
                            handle_update_file(
                                upd_file, self.status, remove=False)
                        if self.status.stop:
                            break
                    if (not self.recursive) or self.status.stop:
                        break

        def start(self):
            self.status.log("monitoring USB")
            self.observer.start()

        def stop(self):
            self.observer.send_stop()

        def join(self):
            self.observer.join()

        @staticmethod
        def get_mountpoint_for_device(dev):
            with open("/proc/mounts") as f:
                for line in f:
                    fields = line.split()
                    try:
                        if fields[0] == dev:
                            return fields[1]
                    except BaseException:
                        pass
                return None

class FileMonitor (UpdateMonitor):

    class EventHandler (pyinotify.ProcessEvent):
        def __init__(self, status):
            pyinotify.ProcessEvent.__init__(self)
            self.status = status

        def process_IN_CLOSE_WRITE(self, event):
            handle_update_file(event.pathname, self.status, remove=True)

    class ObserverThread (threading.Thread):
        def __init__(self, status, monitor):
            threading.Thread.__init__(self, name="ObserverThread")
            self.status = status
            self.monitor = monitor

        def run(self):
            self.status.log("monitoring updated dir")

            while 1:
                if self.monitor.notifier.check_events(timeout=1000):
                    self.monitor.notifier.read_events()
                    self.monitor.notifier.process_events()

                if self.status.stop:
                    if self.status.soapserver:
                        self.status.soapserver.shutdown()
                    return

    def __init__(self, status, update_dir):
        super(FileMonitor, self).__init__(status)
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.Notifier(self.wm)
        self.wm.add_watch(update_dir, pyinotify.IN_CLOSE_WRITE,
                          proc_fun=FileMonitor.EventHandler(self.status))
        self.observer = FileMonitor.ObserverThread(self.status, self)

    def start(self):
        self.observer.start()

    def stop(self):
        pass

    def join(self):
        self.observer.join()
