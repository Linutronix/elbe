# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import json
import pathlib
import tempfile
import uuid

import jsonschema

from elbepack.main import run_elbe_subcommand

here = pathlib.Path(__file__).parent


def generate_test_bom():
    source_dir = here.joinpath('build-simple-example')
    with tempfile.NamedTemporaryFile() as output:
        run_elbe_subcommand([
            'cyclonedx-sbom', '--output', output.name, '-d', source_dir,
        ])
        output.seek(0)
        return json.load(output)


def test_schema():
    test_bom = generate_test_bom()
    with here.joinpath('bom-1.6.schema.json').open() as f:
        bom_schema = json.load(f)
    jsonschema.validate(test_bom, bom_schema)


def test_reference_data():
    test_bom = generate_test_bom()
    test_bom['metadata']['timestamp'] = '0001-01-01T00:00:00+00:00'
    test_bom['serialNumber'] = uuid.UUID(int=0).urn
    test_bom['metadata']['tools'][0]['version'] = 'INVALID'
    with here.joinpath('cyclonedx_reference.json').open() as f:
        reference_data = json.load(f)
    assert test_bom == reference_data
