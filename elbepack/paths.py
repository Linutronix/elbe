# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2014-2026 Linutronix GmbH


class CacheDirs:
    def __init__(self, root='/var/cache/elbe', gnupg_root=None):
        self.root = str(root)
        self.db_dir = self.root
        self.initvm_sources_dir = f'{self.root}/sources'
        self.initvm_binaries_main_dir = f'{self.root}/binaries/main'
        self.initvm_bin_repo_dir = f'{self.root}/initvm-bin-repo'

        if gnupg_root is not None:
            self.gnupg_root = str(gnupg_root)
            self.initvm_gnupg_home = f'{self.gnupg_root}/initvm'
        else:
            self.gnupg_root = None
            self.initvm_gnupg_home = f'{self.root}/gnupg'

        self.initvm_src_repo_dir = f'{self.root}/initvm-src-repo'
        self.installer_dir = f'{self.root}/installer'
        self.devel_dir = f'{self.root}/devel'
        self.devel_elbe = f'{self.devel_dir}/elbe'
        self.source_xml = f'{self.root}/source.xml'

    def project_gnupg_home(self, builddir):
        if self.gnupg_root is not None:
            return f'{self.gnupg_root}/project'
        return f'{builddir}/gnupg'


DEFAULT_CACHE_DIRS = CacheDirs()

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
