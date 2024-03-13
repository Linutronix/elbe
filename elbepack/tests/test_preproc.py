# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020-2021 Linutronix GmbH

from elbepack.directories import run_elbe
from elbepack.tests import parametrize_xml_test_files


@parametrize_xml_test_files('f', 'preproc')
def test_preproc(f):
    run_elbe(['preprocess', f], check=True)
