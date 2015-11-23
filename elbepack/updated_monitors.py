#!/usr/bin/env python

# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (C) 2015 emtrion GmbH
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
import threading
import pyinotify

try:
    import pyudev
    udev_available = True
except ImportError:
    udev_available = False

from elbepack.updated import is_update_file, handle_update_file


class UpdateMonitor(object):
    def __init__(self, status):
        self.status = status

    def start(self):
        raise NotImplemented

    def stop(self):
        raise NotImplemented

    def join(self):
        raise NotImplemented


if udev_available:
    def get_mountpoint_for_device(dev):
        for line in file("/proc/mounts"):
            fields = line.split()
            try:
                if fields[0] == dev:
                    return fields[1]
            except:
                pass
        return None


    class USBMonitor (UpdateMonitor):
        def __init__(self, status, recursive=False):
            super(USBMonitor, self).__init__(status)
            self.recursive = recursive
            self.context = pyudev.Context()
            self.monitor = pyudev.Monitor.from_netlink(self.context)
            self.observer = pyudev.MonitorObserver(self.monitor, self.handle_event)

        def handle_event(self, action, device):
            if ( action == 'add'
                 and device.get('ID_BUS') == 'usb'
                 and device.get('DEVTYPE') == 'partition' ):

                mnt = self.get_mountpoint_for_device(device.device_node)
                if not mnt:
                    self.status.log("Detected USB drive but it was not mounted.")
                    return

                for (dirpath, dirnames, filenames) in os.walk(mnt):
                    # Make sure we process the files in alphabetical order
                    # to get a deterministic behaviour
                    dirnames.sort()
                    filenames.sort()
                    for f in filenames:
                        upd_file = os.path.join(dirpath, f)
                        if is_update_file(upd_file):
                            self.status.log("Found update file '%s' on USB-Device."
                                % upd_file)
                            handle_update_file(upd_file, self.status, remove=False)
                        if self.status.stop:
                            break
                    if (not self.recursive) or self.status.stop:
                        break

        def start(self):
            self.status.log ("monitoring USB")
            self.observer.start()

        def stop(self):
            self.observer.send_stop()

        def join(self):
            self.observer.join()

        def get_mountpoint_for_device(self, dev):
            for line in file("/proc/mounts"):
                fields = line.split()
                try:
                    if fields[0] == dev:
                        return fields[1]
                except:
                    pass
            return None


class FileMonitor (UpdateMonitor):

    class EventHandler (pyinotify.ProcessEvent):
        def __init__ (self, status):
            pyinotify.ProcessEvent.__init__ (self)
            self.status = status

        def process_IN_CLOSE_WRITE (self, event):
            handle_update_file(event.pathname, self.status, remove=True)

    class ObserverThread (threading.Thread):
        def __init__ (self, status, monitor):
            threading.Thread.__init__ (self, name="ObserverThread")
            self.status = status
            self.monitor = monitor

        def run (self):
            self.status.log ("monitoring updated dir")

            while 1:
                if self.monitor.notifier.check_events (timeout=1000):
                    self.monitor.notifier.read_events ()
                    self.monitor.notifier.process_events ()

                if self.status.stop:
                    if self.status.soapserver:
                        self.status.soapserver.shutdown ()
                    return

    def __init__(self, status, update_dir):
        super(FileMonitor, self).__init__(status)
        self.wm = pyinotify.WatchManager ()
        self.notifier = pyinotify.Notifier (self.wm)
        self.wm.add_watch (update_dir, pyinotify.IN_CLOSE_WRITE,
                           proc_fun=FileMonitor.EventHandler (self.status))
        self.observer = FileMonitor.ObserverThread (self.status, self)

    def start(self):
        self.observer.start()

    def stop(self):
        pass

    def join(self):
        self.observer.join()