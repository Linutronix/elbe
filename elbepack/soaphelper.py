# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import socket
import time

from elbepack.cli import CliError


def is_soap_port_reachable(control):
    """
    Test if a service is bound to the soap port.
    """
    try:
        with socket.create_connection((control.host, control.port)):
            pass
    except Exception:
        return False
    return True


def test_soap_communication(control, sleep=10, wait=120):
    """
    Test communication with soap service.

    In case of error, this fuction terminates the command with exit code 123.

    Tests the soap service communication by requesting the list of projects.
    If this works, the communication is ok and the service is up and seems to be healty.
    """
    stop = time.time() + wait
    while True:
        if is_soap_port_reachable(control):
            control.connect()
            try:
                control.list_projects()
            except Exception:
                pass
            else:
                break
        if time.time() > stop:
            raise CliError(123, f'Waited for {wait/60} minutes and the daemon is still not active.')
        print('*', end='', flush=True)
        time.sleep(sleep)
