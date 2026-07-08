# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Linutronix GmbH

import importlib
import os
import pathlib
import struct

import pytest


@pytest.fixture
def elbevalidate():
    for image in pathlib.Path('/boot').glob('vmlinuz-*'):
        if not os.access(image, os.R_OK):
            pytest.skip(f'Kernel image {image} is not readable')

    try:
        return importlib.import_module('elbevalidate')
    except ModuleNotFoundError as e:
        if e.name == 'guestfs':
            pytest.skip(f'module {e.name} not found')
        else:
            raise


_SPARSE_BLOCK_SIZE = 4096
_ZERO_BLOCK = bytes(_SPARSE_BLOCK_SIZE)


def _write_sparse(f, data):
    for i in range(0, len(data), _SPARSE_BLOCK_SIZE):
        block = data[i:i + _SPARSE_BLOCK_SIZE]
        if block == _ZERO_BLOCK[:len(block)]:
            f.seek(len(block), os.SEEK_CUR)
        else:
            f.write(block)


DATA_OFFSET = 2 * 1024 * 1024  # 2MiB


def _round_to(n, g):
    return n + (g - (n % g))


def make_disk(path, parts):
    if len(parts) > 4:
        raise ValueError(parts)

    header = bytearray(512)
    current_data = DATA_OFFSET

    for i, part in enumerate(parts):
        partbytes = bytearray(16)

        rounded_size = _round_to(len(part), 512)

        partbytes[0x04] = 0x83
        partbytes[0x08:0x0C] = struct.pack('<I', current_data // 512)
        partbytes[0x0C:0x10] = struct.pack('<I', rounded_size // 512)

        part_start = 0x01BE + 16 * i
        header[part_start:part_start + 16] = partbytes

        current_data += rounded_size

    header[0x01FE] = 0x55
    header[0x01FF] = 0xAA

    with path.open('wb') as f:
        f.write(header)
        f.seek(DATA_OFFSET - len(header), os.SEEK_CUR)

        for part in parts:
            rounded_size = _round_to(len(part), 512)
            _write_sparse(f, part)
            f.seek(rounded_size - len(part), os.SEEK_CUR)

        f.truncate()
