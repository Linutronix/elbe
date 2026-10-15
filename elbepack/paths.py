# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2026 Linutronix GmbH

ELBE_CACHE_DIR = '/var/cache/elbe'

INITVM_SOURCES_DIR = f'{ELBE_CACHE_DIR}/sources'
INITVM_BINARIES_MAIN_DIR = f'{ELBE_CACHE_DIR}/binaries/main'
INITVM_BIN_REPO_DIR = f'{ELBE_CACHE_DIR}/initvm-bin-repo'
INITVM_GNUPG_HOME = f'{ELBE_CACHE_DIR}/gnupg'
INITVM_SRC_REPO_DIR = f'{ELBE_CACHE_DIR}/initvm-src-repo'
INSTALLER_DIR = f'{ELBE_CACHE_DIR}/installer'
INSTALLER_VMLINUZ = f'{INSTALLER_DIR}/vmlinuz'
INSTALLER_INITRD = f'{INSTALLER_DIR}/initrd-cdrom.gz'
DEVEL_DIR = f'{ELBE_CACHE_DIR}/devel'
DEVEL_ELBE = f'{DEVEL_DIR}/elbe'
SOURCE_XML = f'{ELBE_CACHE_DIR}/source.xml'
DB_PATH = ELBE_CACHE_DIR

# Paths on the deployed target system. Just happens to be the same
# in the build system, but keep separate because there is no relation.
TARGET_CACHE_DIR = '/var/cache/elbe'

TARGET_SOURCES_DIR = f'{TARGET_CACHE_DIR}/sources'
TARGET_BINARIES_MAIN_DIR = f'{TARGET_CACHE_DIR}/binaries/main'
TARGET_BINARIES_ADDED_DIR = f'{TARGET_CACHE_DIR}/binaries/added'
TARGET_REPOS_DIR = f'{TARGET_CACHE_DIR}/repos'
TARGET_REPOS_BASE_DIR = f'{TARGET_REPOS_DIR}/base'
TARGET_UPDATES_DIR = f'{TARGET_CACHE_DIR}/updates'
TARGET_UPDATE_STATE_FILE = f'{TARGET_CACHE_DIR}/update_state.txt'
TARGET_DOWNGRADE_ALLOWED_FILE = f'{TARGET_CACHE_DIR}/.downgrade_allowed'
TARGET_PRE_SCRIPT = f'{TARGET_CACHE_DIR}/pre.sh'
TARGET_POST_SCRIPT = f'{TARGET_CACHE_DIR}/post.sh'
TARGET_GNUPG_HOME = f'{TARGET_CACHE_DIR}/gnupg'
