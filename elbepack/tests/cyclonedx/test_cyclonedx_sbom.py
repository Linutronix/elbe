# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 Linutronix GmbH

import json
import pathlib

import jsonschema

from elbepack.directories import run_elbe

here = pathlib.Path(__file__).parent


def generate_test_bom():
    source_dir = here.joinpath('build-simple-example')
    ps = run_elbe([
        'cyclonedx-sbom', '-d', source_dir,
    ], check=True, capture_output=True)
    return json.loads(ps.stdout)


def test_schema():
    test_bom = generate_test_bom()
    with here.joinpath('bom-1.6.schema.json').open() as f:
        bom_schema = json.load(f)
    jsonschema.validate(test_bom, bom_schema)


def test_reference_data():
    test_bom = generate_test_bom()
    test_bom['metadata']['timestamp'] = 'INVALID'
    test_bom['serialNumber'] = 'INVALID'
    test_bom['metadata']['tools'][0]['version'] = 'INVALID'
    with here.joinpath('cyclonedx_reference.json').open() as f:
        reference_data = json.load(f)
    assert test_bom == reference_data
