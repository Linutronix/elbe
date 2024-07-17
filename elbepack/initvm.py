# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import abc
import contextlib
import importlib
import io
import os
import shutil
import socket
import subprocess
import sys
import textwrap
import time

from elbepack.cli import CliError, with_cli_details
from elbepack.config import cfg
from elbepack.directories import run_elbe
from elbepack.treeutils import etree


def _is_soap_port_reachable():
    """
    Test if a service is bound to the soap port.
    """
    port = int(cfg['soapport'])
    try:
        with socket.create_connection(('127.0.0.1', port)):
            pass
    except Exception:
        return False
    return True


def _test_soap_communication(sleep=10, wait=120):
    """
    Test communication with soap service.

    In case of error, this fuction terminates the command with exit code 123.

    Tests the soap service communication by requesting the list of projects.
    If this works, the communication is ok and the service is up and seems to be healty.
    """
    stop = time.time() + wait
    while True:
        if _is_soap_port_reachable():
            ps = run_elbe(['control', 'list_projects'], capture_output=True, encoding='utf-8')
            if ps.returncode == 0:
                break
        if time.time() > stop:
            raise CliError(123, f'Waited for {wait/60} minutes and the daemon is still not active.')
        print('*', end='', flush=True)
        time.sleep(sleep)


def _build_initvm(directory):
    try:
        subprocess.run(['make'], cwd=directory, check=True)
    except subprocess.CalledProcessError as e:
        raise with_cli_details(e, 147, 'Building the initvm failed')


class _InitVM(abc.ABC):
    @abc.abstractmethod
    def _build(self):
        pass

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def ensure(self):
        pass

    @abc.abstractmethod
    def attach(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def destroy(self):
        pass


class LibvirtInitVM(_InitVM):
    def __init__(self, /, domain, directory, uri='qemu:///system'):
        self._uri = uri
        self._libvirt = importlib.import_module('libvirt', package=__name__)
        self._domain = domain
        self._directory = directory
        self._conn = None

        self._connect()

    def _connect(self):
        if self._conn is not None:
            raise Exception('Already connected')

        try:
            self._conn = self._libvirt.open(self._uri)
        except self._libvirt.libvirtError as verr:
            if not isinstance(verr.args[0], str):
                raise
            if verr.args[0].startswith('Failed to connect socket to'):
                retries = 18
                while retries > 0:
                    retries -= 1
                    time.sleep(10)
                    try:
                        self._conn = self._libvirt.open(self._uri)
                    except self._libvirt.libvirtError as verr:
                        if not isinstance(verr.args[0], str):
                            raise
                        if verr.args[0].startswith('Failed to connect socket to'):
                            pass

                    if self._conn:
                        break

                if not self._conn:
                    raise CliError(118, textwrap.dedent("""
                        Accessing libvirt provider system not possible.
                        Even after waiting 180 seconds.
                        Make sure that package 'libvirt-daemon-system' is
                        installed, and the service is running properly."""))

            elif verr.args[0].startswith('authentication unavailable'):
                raise CliError(119, textwrap.dedent("""
                    Accessing libvirt provider system not allowed.
                    Users which want to use elbe'
                    need to be members of the 'libvirt' group.
                    'gpasswd -a <user> libvirt' and logging in again,
                    should fix the problem."""))

            elif verr.args[0].startswith('error from service: CheckAuthorization'):
                raise CliError(120, textwrap.dedent("""
                    Accessing libvirt failed.
                    Probably entering the password for accssing libvirt
                    timed out. If this occured after 'elbe initvm create'
                    it should be safe to use 'elbe initvm start' to continue."""))

            else:
                # In case we get here, the exception is unknown, and we want to see it
                raise

    def _get_domain(self):
        doms = self._conn.listAllDomains()

        for d in doms:
            if d.name() == self._domain:
                return d

    @staticmethod
    def _state(domain):
        return domain.info()[0]

    def _libvirt_enable_kvm(self, xml):
        caps_tree = etree(io.StringIO(self._conn.getCapabilities()))
        domain_tree = etree(io.StringIO(xml))

        arch = domain_tree.et.find('.//os/type').attrib['arch']

        if caps_tree.et.find('.//guest/arch[@name="' + arch + '"]/domain[@type="kvm"]') is None:
            return xml

        domain_tree.root.et.attrib['type'] = 'kvm'
        return domain_tree.tostring()

    def _build(self):
        if self._get_domain() is not None:
            raise CliError(142, textwrap.dedent(f"""
                Initvm is already defined for the libvirt domain '{cfg['initvm_domain']}'.
                If you want to build in your old initvm, use `elbe initvm submit <xml>`.')
                If you want to remove your old initvm from libvirt run `elbe initvm destroy`.
                You can specify another libvirt domain by setting the
                ELBE_INITVM_DOMAIN environment variable to an unused domain name.
                Note:
                \t1) You can reimport your old initvm via
                `virsh --connect qemu:///system define <file>`
                \t   where <file> is the corresponding libvirt.xml
                \t2) virsh --connect qemu:///system undefine does not delete the image
                of your old initvm."""))

        _build_initvm(self._directory)

        # Read xml file for libvirt.
        with open(os.path.join(self._directory, 'libvirt.xml')) as f:
            xml = f.read()

        xml = self._libvirt_enable_kvm(xml)

        # Register initvm in libvirt.
        try:
            self._conn.defineXML(xml)
        except Exception as e:
            raise with_cli_details(e, 146, textwrap.dedent("""
                Registering initvm in libvirt failed.
                Try `elbe initvm destroy` to delete existing initvm."""))

    @staticmethod
    def _attach_disk_fds(domain):
        # libvirt does not necessarily have permissions to directly access the
        # image file. libvirt 9.0 provides FDAssociate() to pass an open file
        # descriptor to libvirt which is used to access files via the context
        # of the client, which has permissions.

        if not hasattr(domain, 'FDAssociate'):
            return

        xml = etree(io.StringIO(domain.XMLDesc()))
        disk = xml.et.find('.//devices/disk')

        for source in disk.findall('.//source'):
            flags = os.O_RDWR if source.getparent() is disk else os.O_RDONLY
            # Use raw unmanaged FDs as libvirt will take full ownership of them.
            domain.FDAssociate(source.attrib['fdgroup'], [
                os.open(source.attrib['file'], flags),
            ])

    def start(self):
        domain = self._get_domain()

        state = self._state(domain)
        if state == self._libvirt.VIR_DOMAIN_RUNNING:
            raise CliError(122, 'Initvm already running.')
        elif state == self._libvirt.VIR_DOMAIN_SHUTOFF:
            self._attach_disk_fds(domain)

            # Domain is shut off. Let's start it!
            domain.create()
            # Wait five seconds for the initvm to boot
            # TODO: Instead of waiting for five seconds
            # check whether SOAP server is reachable.
            for _ in range(1, 5):
                sys.stdout.write('*')
                sys.stdout.flush()
                time.sleep(1)
            print('*')

    def ensure(self):
        state = self._state(self._get_domain())
        if state == self._libvirt.VIR_DOMAIN_SHUTOFF:
            self.start()
        elif state == self._libvirt.VIR_DOMAIN_RUNNING:
            _test_soap_communication()
        else:
            raise CliError(124, 'Elbe initvm in bad state.')

    def stop(self):
        domain = self._get_domain()
        state = self._state(domain)

        if state != self._libvirt.VIR_DOMAIN_RUNNING:
            raise CliError(125, 'Initvm is not running.')

        while True:
            sys.stdout.write('*')
            sys.stdout.flush()
            time.sleep(1)

            state = self._state(domain)

            if state == self._libvirt.VIR_DOMAIN_SHUTDOWN:
                continue

            if state == self._libvirt.VIR_DOMAIN_SHUTOFF:
                break

            try:
                domain.shutdown()
            except self._libvirt.libvirtError as e:
                raise e

        print('\nInitvm shutoff')

    def attach(self):
        if self._state(self._get_domain()) != self._libvirt.VIR_DOMAIN_RUNNING:
            raise CliError(126, 'Error: Initvm not running properly.')

        print('Attaching to initvm console.')
        subprocess.run(['virsh', '--connect', 'qemu:///system', 'console', cfg['initvm_domain']],
                       check=True)

    def destroy(self):
        domain = self._get_domain()
        if domain is not None:
            with contextlib.suppress(self._libvirt.libvirtError):
                domain.destroy()
            with contextlib.suppress(self._libvirt.libvirtError):
                domain.undefine()
        shutil.rmtree(self._directory, ignore_errors=True)


class QemuInitVM(_InitVM):
    def __init__(self, /, directory):
        self._directory = directory

    def _get_initvmdir(self):
        if not os.path.isdir(self._directory):
            raise CliError(207, 'No initvm found!')

        return self._directory

    def _build(self):
        _build_initvm(self._directory)

    def start(self):
        initvmdir = self._get_initvmdir()

        # Test if there is already a process bound to the expected port.
        if _is_soap_port_reachable():
            if os.path.exists(os.path.join(initvmdir, 'qemu-monitor-socket')):
                # If the unix socket exists, assume this VM is bound to the soap port.
                print('This initvm is already running.')
            else:
                # If no unix socket file is found, assume another VM is bound to the soap port.
                raise CliError(211, 'There is already another running initvm.\n'
                                    'Please stop this VM first.')
        else:
            # Try to start the QEMU VM for the given directory.
            try:
                subprocess.Popen(['make', 'run_qemu'], cwd=initvmdir)
            except Exception as e:
                raise with_cli_details(e, 211, 'Running QEMU failed')

            # This will sys.exit on error.
            _test_soap_communication(sleep=1, wait=60)
            print('initvm started successfully')

    def ensure(self):
        if not _is_soap_port_reachable():
            raise CliError(206, 'Elbe initvm in bad state.\nNo process found on soap port.')

    def stop(self):
        """
        Stop the QEMU initvm.

        This method tries to stop the QEMU initvm by sending a poweroff event
        using QEMU monitor.
        """
        initvmdir = self._get_initvmdir()

        socket_path = os.path.join(initvmdir, 'qemu-monitor-socket')

        # Test if QEMU monitor unix-socket file exists, and error exit if not.
        if not os.path.exists(socket_path):
            raise CliError(212, 'No unix socket found for this vm!\nunable to shutdown this vm.')

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(socket_path)
                client.sendall(b'system_powerdown\n')
                # Give monitor time to react - closing too early stops command processing.
                time.sleep(2)
        except Exception:
            # Shutting down the VM will break the connection.
            pass

        if _is_soap_port_reachable():
            print('\nstopping initvm failed!')
        else:
            print('\ninitvm stopped successfully')

    def attach(self):
        """
        Attach to QEMU initvm.

        This method is using socat to connect to the unix-socket of the
        serial console of the initvm.
        """
        initvmdir = self._get_initvmdir()

        # Test if socat command is available.
        if shutil.which('socat') is None:
            raise CliError(208, 'The command "socat" is required.\n'
                                'Please install socat: sudo apt install socat')

        # Connect to socket file, if it exists.
        if os.path.exists(os.path.join(initvmdir, 'vm-serial-socket')):
            subprocess.run(['socat', 'stdin,raw,echo=0,escape=0x11',
                            'unix-connect:vm-serial-socket'],
                           cwd=initvmdir, check=False)
        else:
            msg = 'No unix socket found for the console of this vm!\nUnable to attach.'
            if _is_soap_port_reachable():
                msg += '\nThere seems to be another initvm running. The soap port is in use.'
            raise CliError(212, msg)

    def destroy(self):
        shutil.rmtree(self._directory, ignore_errors=True)
