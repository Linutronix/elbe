# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import enum


class PartitionLabel(enum.StrEnum):
    DOS = 'msdos'
    GPT = 'gpt'


class GPTPartitionType(str):
    EFI_SYSTEM_PARTITION = 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'
    LINUX_FILESYSTEM = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'
