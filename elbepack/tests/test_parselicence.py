# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import contextlib
import io
import pathlib
import re

from elbepack.main import run_elbe_subcommand

here = pathlib.Path(__file__).parent


def _replace_changing_spdx_data(s):
    s = re.sub(r'\nCreator: Tool: .*\n', r'\nCreator: Tool: INVALID\n', s)
    s = re.sub(r'\nCreated: .*\n', r'\nCreated: 0001-01-01T00:00:00+00:00\n', s)
    return s


def test_parselicence(tmp_path):
    xml_output = tmp_path.joinpath('licences.xml')
    spdx_output = tmp_path.joinpath('licences.spdx')
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        run_elbe_subcommand([
            'parselicence',
            '--mapping', here.joinpath('cyclonedx', 'example-mapping.xml'),
            '--output', xml_output,
            '--tvout', spdx_output,
            here.joinpath('cyclonedx', 'build-simple-example', 'licence-target.xml'),
        ])

    assert stdout.getvalue() == 'statistics:'\
           '\ntotal_pkgs=156' \
           ' num_machine_readable=137' \
           ' num_heuristics=3' \
           ' num_error_pkgs=86\n'

    xml_reference = here.joinpath('test_parselicence_reference.xml')
    assert xml_output.read_text() == xml_reference.read_text()

    spdx_reference = here.joinpath('test_parselicence_reference.spdx')
    assert _replace_changing_spdx_data(spdx_output.read_text()) == spdx_reference.read_text()
