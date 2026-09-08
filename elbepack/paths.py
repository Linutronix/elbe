# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2026 Linutronix GmbH

ELBE_CACHE_DIR = '/var/cache/elbe'

SOURCES_DIR = f'{ELBE_CACHE_DIR}/sources'
BINARIES_MAIN_DIR = f'{ELBE_CACHE_DIR}/binaries/main'
BINARIES_ADDED_DIR = f'{ELBE_CACHE_DIR}/binaries/added'
INITVM_BIN_REPO_DIR = f'{ELBE_CACHE_DIR}/initvm-bin-repo'
INITVM_GNUPG_HOME = f'{ELBE_CACHE_DIR}/gnupg'
INITVM_SRC_REPO_DIR = f'{ELBE_CACHE_DIR}/initvm-src-repo'
INSTALLER_DIR = f'{ELBE_CACHE_DIR}/installer'
INSTALLER_VMLINUZ = f'{INSTALLER_DIR}/vmlinuz'
INSTALLER_INITRD = f'{INSTALLER_DIR}/initrd-cdrom.gz'
DEVEL_DIR = f'{ELBE_CACHE_DIR}/devel'
DEVEL_ELBE = f'{DEVEL_DIR}/elbe'
REPOS_DIR = f'{ELBE_CACHE_DIR}/repos'
REPOS_BASE_DIR = f'{REPOS_DIR}/base'
UPDATES_DIR = f'{ELBE_CACHE_DIR}/updates'
SOURCE_XML = f'{ELBE_CACHE_DIR}/source.xml'
UPDATE_STATE_FILE = f'{ELBE_CACHE_DIR}/update_state.txt'
DOWNGRADE_ALLOWED_FILE = f'{ELBE_CACHE_DIR}/.downgrade_allowed'
DB_PATH = ELBE_CACHE_DIR
PRE_SCRIPT = f'{ELBE_CACHE_DIR}/pre.sh'
POST_SCRIPT = f'{ELBE_CACHE_DIR}/post.sh'

# Path on deployed target system. Just happens to be the same
# in the build system, but keep separate because there is no relation.
TARGET_GNUPG_HOME = '/var/cache/elbe/gnupg'
