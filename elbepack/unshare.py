# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

"""
Low-level unshare and namespace/mount primitives.
"""

import ctypes
import grp
import os
import pwd
import subprocess
from pathlib import Path


_CLONE_NEWUSER = 0x10000000
_CLONE_NEWNS = 0x00020000

_MS_BIND = 4096
_MS_REC = 16384

# Used to track whether the calling process has already unshared itself
_process_unshared = False


def _unshare(flags):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.unshare(flags) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))


def _read_subid_range(path, name):
    with open(path) as f:
        for line in f:
            entry_name, start, count = line.strip().split(':')
            if entry_name == name:
                return int(start), int(count)
    raise LookupError(f'no {path} entry for {name!r}')


def _passthrough_id_map(current_map_content):
    lines = []
    for line in current_map_content.strip().splitlines():
        inner, _outer, count = line.split()
        lines.append(f'{inner} {inner} {count}')
    return '\n'.join(lines) + '\n'


def _setup_id_mapping(my_pid, as_root=False):
    if as_root:
        # If we are already root, we might be in one of two situations
        #
        # 1.) We are truely root (e.g. inside an initvm).
        #     Strictly speaking, we would not need to unshare into new user namespace.
        # 2.) We are inside a container where root is already mapped and does not
        #     correspond to the true root on the host. In that case, we still lack
        #     CAP_SYS_ADMIN, i.e. cannot mount, but can also not use --map-auto
        #     to perform a new mapping as root. We can, however, just reuse the existing
        #     mapping. That also does not hurt for the first situation.
        with open('/proc/self/uid_map') as f:
            uid_map = _passthrough_id_map(f.read())
        with open('/proc/self/gid_map') as f:
            gid_map = _passthrough_id_map(f.read())

        Path(f'/proc/{my_pid}/uid_map').write_text(uid_map)
        Path(f'/proc/{my_pid}/gid_map').write_text(gid_map)
    else:
        # As non-root, use newuidmap/newgidmap
        uid = os.getuid()
        gid = os.getgid()
        username = pwd.getpwuid(uid).pw_name
        groupname = grp.getgrgid(gid).gr_name

        subuid_start, subuid_count = _read_subid_range('/etc/subuid', username)
        subgid_start, subgid_count = _read_subid_range('/etc/subgid', groupname)

        # Map root in new namespace to current user on host
        subprocess.run(['newuidmap', str(my_pid),
                        '0', str(uid), '1',
                        '1', str(subuid_start), str(subuid_count)], check=True)
        subprocess.run(['newgidmap', str(my_pid),
                        '0', str(gid), '1',
                        '1', str(subgid_start), str(subgid_count)], check=True)


def unshare_inplace():
    global _process_unshared

    my_pid = os.getpid()
    as_root = os.geteuid() == 0

    ready_r, ready_w = os.pipe()

    mapper_pid = os.fork()
    if mapper_pid == 0:
        os.close(ready_w)
        os.read(ready_r, 1)
        os.close(ready_r)
        try:
            _setup_id_mapping(my_pid, as_root=as_root)
            os._exit(0)
        except (OSError, subprocess.CalledProcessError, LookupError):
            os._exit(1)

    os.close(ready_r)

    _unshare(_CLONE_NEWUSER)

    # Signal child to set up mappings
    os.write(ready_w, b'x')
    os.close(ready_w)

    # Wait for child to finish
    _, status = os.waitpid(mapper_pid, 0)
    if status != 0:
        raise OSError('failed to set up the uid/gid mapping for the new namespace')

    # Unshare mount namespace
    _unshare(_CLONE_NEWNS)

    _process_unshared = True


def _set_c_locale():
    os.environ['LANG'] = 'C'
    os.environ['LANGUAGE'] = 'C'
    os.environ['LC_ALL'] = 'C'


def _bind_mount_pseudo_filesystems(directory):
    if directory == '/':
        return

    libc = ctypes.CDLL(None, use_errno=True)
    for fs in ('proc', 'sys', 'dev'):
        src = f'/{fs}'
        dst = os.path.join(directory, fs)
        os.makedirs(dst, exist_ok=True)
        ret = libc.mount(src.encode(), dst.encode(), None,
                         ctypes.c_ulong(_MS_BIND | _MS_REC), None)
        if ret != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f'mount({src!r}, {dst!r}): {os.strerror(errno)}')


def enter_chroot_inplace(directory):
    global _process_unshared
    assert _process_unshared, 'Internal error: process not yet unshared'

    _set_c_locale()

    if directory == '/':
        return

    _bind_mount_pseudo_filesystems(directory)
    os.chdir(directory)
    os.chroot(directory)


def run_in_chroot(directory, fn, *args, env_add=None, **kwargs):
    pid = os.fork()
    if pid == 0:
        _set_c_locale()
        if env_add:
            os.environ.update(env_add)

        try:
            unshare_inplace()

            if directory != '/':
                _bind_mount_pseudo_filesystems(directory)
                os.chdir(directory)
                os.chroot(directory)

            fn(*args, **kwargs)
            os._exit(0)
        except Exception:
            os._exit(1)
    else:
        _, status = os.waitpid(pid, 0)
        if status != 0:
            raise OSError('chrooted function failed in child process')


def run_unshared(fn, *args, **kwargs):
    pid = os.fork()
    if pid == 0:
        # Child process: unshare and run the function
        try:
            unshare_inplace()
            fn(*args, **kwargs)
            os._exit(0)
        except Exception:
            os._exit(1)
    else:
        # Parent process: wait for child
        _, status = os.waitpid(pid, 0)
        if status != 0:
            raise OSError('unshared function failed in child process')
