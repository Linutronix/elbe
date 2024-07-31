# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2018 Linutronix GmbH
# SPDX-FileCopyrightText: 2016 Claudius Heine <ch@denx.de>

import binascii
import logging
import socket
import sys
import time
from http.client import BadStatusLine
from urllib.error import URLError

from suds.client import Client

from elbepack.version import elbe_version


class ElbeVersionMismatch(RuntimeError):
    def __init__(self, client_version, server_version):
        self.client_version = client_version
        self.server_version = server_version
        super().__init__(f'Client: {client_version} Server: {server_version}')

    @classmethod
    def check(cls, client_version, server_version):
        if client_version != server_version:
            raise cls(client_version, server_version)


def set_suds_debug(debug):
    if debug:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger('suds.client').setLevel(logging.DEBUG)
        logging.getLogger('suds.transport').setLevel(logging.DEBUG)
        logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
        logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)
        logging.getLogger('suds.resolver').setLevel(logging.DEBUG)
        logging.getLogger('suds.umx.typed').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.CRITICAL)
        logging.getLogger('suds.umx.typed').setLevel(logging.ERROR)
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)


class ElbeSoapClient:
    def __init__(self, host, port, user, passwd, timeout, retries=10, debug=False):

        # Mess with suds logging, for debug, or squelch warnings
        set_suds_debug(debug)

        # Attributes
        self.wsdl = 'http://' + host + ':' + str(port) + '/soap/?wsdl'
        control = None
        current_retries = 0

        # Loop and try to connect
        while control is None:
            current_retries += 1
            try:
                control = Client(self.wsdl, timeout=timeout)
            except URLError as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)
            except socket.error as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)
            except BadStatusLine as e:
                if current_retries > retries:
                    raise e
                time.sleep(1)

        # Make sure, that client.service still maps
        # to the service object.
        self.service = control.service

        ElbeVersionMismatch.check(elbe_version, self.service.get_version())

        # We have a Connection, now login
        self.service.login(user, passwd)

    def download_file(self, builddir, filename, dst_fname):
        fp = open(dst_fname, 'wb')
        part = 0

        # XXX the retry logic might get removed in the future, if the error
        # doesn't occur in real world. If it occurs, we should think about
        # the root cause instead of stupid retrying.
        retry = 5

        while True:
            try:
                ret = self.service.get_file(builddir, filename, part)
            except BadStatusLine as e:
                retry = retry - 1

                print(f'get_file part {part} failed, retry {retry} times',
                      file=sys.stderr)
                print(str(e), file=sys.stderr)
                print(repr(e.line), file=sys.stderr)

                if not retry:
                    fp.close()
                    print('file transfer failed', file=sys.stderr)
                    sys.exit(170)

            if ret == 'FileNotFound':
                print(ret, file=sys.stderr)
                sys.exit(171)
            if ret == 'EndOfFile':
                fp.close()
                return

            fp.write(binascii.a2b_base64(ret))
            part = part + 1
